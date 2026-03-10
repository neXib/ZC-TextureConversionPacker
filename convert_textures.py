#!/usr/bin/env python3
"""
Megascans EXR to PNG Texture Converter
Converts EXR texture sets to PNG with custom channel packing:
- 4K_DR: RGB from Diffuse + Green from ORDp as Alpha
- 4K_ND: RGB from Normal + Blue from ORDp as Alpha
"""

import os
import sys
from pathlib import Path
from PIL import Image
import OpenEXR
import Imath
import numpy as np


def read_exr_channels(exr_path):
    """Read all channels from an EXR file and return as numpy arrays."""
    exr_file = OpenEXR.InputFile(str(exr_path))
    header = exr_file.header()

    dw = header['dataWindow']
    size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)

    channels = {}
    channel_names = header['channels'].keys()

    FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)

    for channel_name in channel_names:
        channel_data = exr_file.channel(channel_name, FLOAT)
        channel_array = np.frombuffer(channel_data, dtype=np.float32)
        channel_array = channel_array.reshape(size[1], size[0])
        channels[channel_name] = channel_array

    return channels, size


def exr_to_pil_image(exr_path, channels_to_use=['R', 'G', 'B']):
    """Convert EXR channels to PIL Image."""
    channels, size = read_exr_channels(exr_path)

    # Prepare arrays for each channel
    arrays = []
    for ch in channels_to_use:
        if ch in channels:
            # Clamp and convert to 8-bit
            arr = np.clip(channels[ch] * 255, 0, 255).astype(np.uint8)
            arrays.append(arr)
        else:
            # If channel missing, create empty channel
            arrays.append(np.zeros((size[1], size[0]), dtype=np.uint8))

    if len(arrays) == 3:
        rgb_array = np.stack(arrays, axis=-1)
        return Image.fromarray(rgb_array, 'RGB')
    elif len(arrays) == 4:
        rgba_array = np.stack(arrays, axis=-1)
        return Image.fromarray(rgba_array, 'RGBA')
    else:
        raise ValueError(f"Unsupported number of channels: {len(arrays)}")


def get_channel_from_exr(exr_path, channel_name):
    """Extract a single channel from an EXR file as uint8 array."""
    channels, size = read_exr_channels(exr_path)

    if channel_name in channels:
        arr = np.clip(channels[channel_name] * 255, 0, 255).astype(np.uint8)
        return arr
    else:
        print(f"Warning: Channel '{channel_name}' not found in {exr_path}")
        return np.zeros((size[1], size[0]), dtype=np.uint8)


def process_texture_set_from_template(file_paths, output_dir, base_name, template):
    """
    Process a set of textures using a template configuration.

    Args:
        file_paths: Dictionary mapping file types to paths (e.g., {'D': path, 'N': path, 'ORDp': path})
        output_dir: Output directory path
        base_name: Base name for output files
        template: Template dictionary defining outputs and channel mappings
    """
    print(f"Processing texture set: {base_name}")

    try:
        # Read all input files
        file_data = {}
        for file_type, file_path in file_paths.items():
            channels, size = read_exr_channels(file_path)
            file_data[file_type] = channels

        # Process each output defined in the template
        for output_def in template['outputs']:
            output_name = output_def['name']
            channel_mapping = output_def['channels']
            gamma_correct = output_def.get('gamma_correct', False)

            # Extract channels according to mapping
            output_channels = []
            for mapping in channel_mapping:
                source_file = mapping['source']
                source_channel = mapping['channel']

                if source_file in file_data:
                    channels = file_data[source_file]
                    # Try both uppercase and lowercase channel names
                    channel_data = channels.get(source_channel, channels.get(source_channel.lower(), 0))
                    if isinstance(channel_data, np.ndarray):
                        channel_array = np.clip(channel_data * 255, 0, 255).astype(np.uint8)
                    else:
                        # If channel not found, create empty channel
                        channel_array = np.zeros(size[1::-1], dtype=np.uint8)
                else:
                    channel_array = np.zeros(size[1::-1], dtype=np.uint8)

                output_channels.append(channel_array)

            # Apply gamma correction if needed
            if gamma_correct:
                gamma = 1.0 / 2.2
                output_channels = [
                    (np.power(ch / 255.0, gamma) * 255.0).astype(np.uint8)
                    for ch in output_channels
                ]

            # Create output image
            if len(output_channels) == 3:
                output_array = np.stack(output_channels, axis=-1)
                output_image = Image.fromarray(output_array, 'RGB')
            elif len(output_channels) == 4:
                output_array = np.stack(output_channels, axis=-1)
                output_image = Image.fromarray(output_array, 'RGBA')
            else:
                print(f"  ERROR: Unsupported number of channels: {len(output_channels)}")
                continue

            output_path = output_dir / f"{base_name}_4K_{output_name}.png"
            output_image.save(output_path, 'PNG')
            print(f"  Created: {output_path.name}")

        return True

    except Exception as e:
        print(f"  ERROR processing {base_name}: {str(e)}")
        return False


def process_texture_set(diffuse_path, normal_path, ordp_path, output_dir, base_name):
    """
    Process a set of textures and create the two output images.

    Args:
        diffuse_path: Path to 4K_D (Diffuse) EXR file
        normal_path: Path to 4K_N (Normal) EXR file
        ordp_path: Path to 4K_ORDp (Combined mask) EXR file
        output_dir: Output directory path
        base_name: Base name for output files
    """
    print(f"Processing texture set: {base_name}")

    try:
        # Read diffuse RGB
        diffuse_channels, _ = read_exr_channels(diffuse_path)
        diffuse_r = np.clip(diffuse_channels.get('R', diffuse_channels.get('r', 0)) * 255, 0, 255).astype(np.uint8)
        diffuse_g = np.clip(diffuse_channels.get('G', diffuse_channels.get('g', 0)) * 255, 0, 255).astype(np.uint8)
        diffuse_b = np.clip(diffuse_channels.get('B', diffuse_channels.get('b', 0)) * 255, 0, 255).astype(np.uint8)

        # Read normal RGB
        normal_channels, _ = read_exr_channels(normal_path)
        normal_r = np.clip(normal_channels.get('R', normal_channels.get('r', 0)) * 255, 0, 255).astype(np.uint8)
        normal_g = np.clip(normal_channels.get('G', normal_channels.get('g', 0)) * 255, 0, 255).astype(np.uint8)
        normal_b = np.clip(normal_channels.get('B', normal_channels.get('b', 0)) * 255, 0, 255).astype(np.uint8)

        # Read ORDp channels (O=AO, R=Roughness, D=Displacement, p=unknown)
        ordp_channels, _ = read_exr_channels(ordp_path)
        ordp_g = np.clip(ordp_channels.get('G', ordp_channels.get('g', 0)) * 255, 0, 255).astype(np.uint8)  # Roughness
        ordp_b = np.clip(ordp_channels.get('B', ordp_channels.get('b', 0)) * 255, 0, 255).astype(np.uint8)  # Displacement

        # Create 4K_DR: RGB from diffuse, Alpha from ORDp green (roughness)
        # Apply gamma correction for sRGB (diffuse textures should be in sRGB space)
        gamma = 1.0 / 2.2
        diffuse_r_srgb = np.power(diffuse_r / 255.0, gamma) * 255.0
        diffuse_g_srgb = np.power(diffuse_g / 255.0, gamma) * 255.0
        diffuse_b_srgb = np.power(diffuse_b / 255.0, gamma) * 255.0
        ordp_g_srgb = np.power(ordp_g / 255.0, gamma) * 255.0

        dr_array = np.stack([
            diffuse_r_srgb.astype(np.uint8),
            diffuse_g_srgb.astype(np.uint8),
            diffuse_b_srgb.astype(np.uint8),
            ordp_g_srgb.astype(np.uint8)
        ], axis=-1)
        dr_image = Image.fromarray(dr_array, 'RGBA')
        dr_output = output_dir / f"{base_name}_4K_DR.png"
        dr_image.save(dr_output, 'PNG')
        print(f"  Created: {dr_output.name}")

        # Create 4K_ND: RGB from normal, Alpha from ORDp blue (displacement)
        # Normal maps stay linear (no gamma correction)
        nd_array = np.stack([normal_r, normal_g, normal_b, ordp_b], axis=-1)
        nd_image = Image.fromarray(nd_array, 'RGBA')
        nd_output = output_dir / f"{base_name}_4K_ND.png"
        nd_image.save(nd_output, 'PNG')
        print(f"  Created: {nd_output.name}")

        return True

    except Exception as e:
        print(f"  ERROR processing {base_name}: {str(e)}")
        return False


def find_texture_sets(input_dir, log_func=None, required_files=None):
    """
    Find all texture sets in the input directory (including subdirectories).
    Matches files by their unique ID (the part before _4K_X).
    Returns a list of tuples: (file_paths_dict, base_name)
    """
    if log_func is None:
        log_func = print

    if required_files is None:
        required_files = ['D', 'N', 'ORDp']

    input_path = Path(input_dir)
    texture_sets = {}

    # Find all EXR files (both .exr and .EXR)
    exr_files = list(input_path.rglob("*.exr")) + list(input_path.rglob("*.EXR"))

    log_func(f"Found {len(exr_files)} EXR files total")

    for exr_file in exr_files:
        filename = exr_file.stem
        log_func(f"Checking file: {filename}")

        # Extract the unique ID and file type
        # Example: T_Forest_Floor_wgxsded_4K_D -> ID: wgxsded, Type: D
        if "_4K_" in filename:
            parts = filename.split("_4K_")
            if len(parts) == 2:
                prefix = parts[0]
                file_type = parts[1]  # e.g., "D", "N", "ORDp"

                # Extract ID (last part after underscore in prefix)
                id_match = prefix.split("_")
                unique_id = id_match[-1] if id_match else prefix

                # Check if this file type is required
                if file_type in required_files:
                    if unique_id not in texture_sets:
                        texture_sets[unique_id] = {'folder': exr_file.parent, 'files': {}}
                    texture_sets[unique_id]['files'][file_type] = exr_file
                    log_func(f"  -> Found {file_type} with ID '{unique_id}'")

    # Filter complete sets (must have all required files)
    complete_sets = []
    for unique_id, data in texture_sets.items():
        files = data['files']
        if all(file_type in files for file_type in required_files):
            # Use the first file's name as base name for output
            first_file = files[required_files[0]]
            base_name = first_file.stem.rsplit('_4K_', 1)[0]
            complete_sets.append((
                files,
                base_name
            ))
            log_func(f"Complete set with ID '{unique_id}': {base_name}", 'success' if hasattr(log_func, '__self__') else 'info')
        else:
            missing = [ft for ft in required_files if ft not in files]
            log_func(f"Incomplete set for ID '{unique_id}', missing: {missing}", 'warning' if hasattr(log_func, '__self__') else 'info')

    return complete_sets


def main():
    """Main conversion workflow."""
    if len(sys.argv) != 3:
        print("Usage: python convert_textures.py <input_directory> <output_directory>")
        print("\nExample:")
        print("  python convert_textures.py ./input_textures ./output_textures")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Validate input directory
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Scanning for texture sets in: {input_dir}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    # Find all texture sets
    texture_sets = find_texture_sets(input_dir)

    if not texture_sets:
        print("No complete texture sets found!")
        print("Looking for files matching patterns: *_4K_D.exr, *_4K_N.exr, *_4K_ORDp.exr")
        sys.exit(1)

    print(f"Found {len(texture_sets)} complete texture set(s)\n")

    # Process each set
    successful = 0
    failed = 0

    for diffuse_path, normal_path, ordp_path, base_name in texture_sets:
        if process_texture_set(diffuse_path, normal_path, ordp_path, output_path, base_name):
            successful += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"Conversion complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")


if __name__ == "__main__":
    main()
