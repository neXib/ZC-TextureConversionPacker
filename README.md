# ZetiCeta Texture Converter and Packer

A Flask-based web application for converting EXR textures to PNG format with customizable channel packing for Unreal Engine workflows.
It is setup for Megascans EXR files now, but might be extended in the future to support more input formats. 

## Features

- **Web-based UI** - Easy-to-use interface for texture conversion
- **Custom Channel Packing** - Combine multiple texture channels into optimized output files
- **Flexible Templates** - Built-in templates and support for custom user templates
- **Resolution Control** - Convert to different resolutions (8K, 4K, 2K, 1K)
- **Batch Processing** - Automatically processes all texture sets in a directory
- **Real-time Progress** - Live progress tracking and detailed logs
- **Directory Browser** - Built-in file system browser for easy path selection

## Prerequisites

### Python Requirements
- Python 3.7 or higher
- pip (Python package installer)

### Required Python Packages
```bash
pip install flask flask-cors pillow openexr numpy
```

### System Dependencies

#### Windows
- Visual C++ Redistributable (usually already installed)
- No additional dependencies required

#### Linux/Mac
OpenEXR library may need to be installed:

**Ubuntu/Debian:**
```bash
sudo apt-get install libopenexr-dev openexr
```

**macOS (with Homebrew):**
```bash
brew install openexr
```

**Fedora/RHEL:**
```bash
sudo dnf install OpenEXR-devel
```

## Installation

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd ImageTextureConversion
   ```

2. **Install Python dependencies**
   ```bash
   pip install flask flask-cors pillow openexr numpy
   ```

3. **Verify installation**
   ```bash
   python app.py
   ```
   The application should start and open in your browser at `http://localhost:5000`

## Usage

### Starting the Application

#### Windows
Double-click `start.bat` or run:
```bash
python app.py
```

#### Linux/Mac
```bash
python3 app.py
```

The application will automatically open in your default web browser.

### Using the Web Interface

1. **Select a Template**
   - Choose from built-in templates (DR,ND or DR,NOD)
   - Or create your own custom template

2. **Choose Output Resolution**
   - "Same as Input" - Maintains original resolution
   - 8K, 4K, 2K, or 1K - Downsamples to selected resolution

3. **Select Input Directory**
   - Click "Browse..." to navigate your file system
   - Choose the folder containing your Megascans EXR files
   - Supports recursive search through subdirectories

4. **Select Output Directory**
   - Click "Browse..." to choose where converted files will be saved
   - Directory will be created if it doesn't exist

5. **Start Conversion**
   - Click "Start Conversion"
   - Monitor progress in real-time
   - Check logs for detailed information

### Input File Format

The application expects Megascans EXR files with the following naming pattern:
```
<name>_<UniqueID>_<Resolution>_<Type>.exr
```

Examples:
- `T_Forest_Floor_wgxsded_4K_D.exr` (Diffuse)
- `T_Forest_Floor_wgxsded_4K_N.exr` (Normal)
- `T_Forest_Floor_wgxsded_4K_ORDp.exr` (Occlusion, Roughness, Displacement)

Supported resolutions: 8K, 4K, 2K, 1K

### Built-in Templates

#### DR,ND Template (Default)
Creates two output files:
- **DR (Diffuse + Roughness)**: RGB from Diffuse + Roughness in Alpha (with gamma correction)
- **ND (Normal + Displacement)**: RGB from Normal + Displacement in Alpha (linear)

#### DR,NOD Template
Creates two output files:
- **DR (Diffuse + Roughness)**: RGB from Diffuse + Roughness in Alpha (with gamma correction)
- **NOD (Normal RG + Occlusion + Displacement)**: RG from Normal + Occlusion in B + Displacement in Alpha (linear)

### Creating Custom Templates

1. Click **"+ Create Template"** button
2. Fill in template details:
   - **Template ID**: Unique identifier (lowercase, underscores only)
   - **Name**: Display name
   - **Description**: Brief description
   - **Input Files**: Comma-separated list (e.g., `D,N,ORDp`)

3. Define output files:
   - **Output Name**: Suffix for output file (e.g., `DR`)
   - **Gamma Correction**: Enable for color textures, disable for data textures
   - **Channel Mappings**: Define how channels are packed
     - Source File: Which input file to read from
     - Source Channel: Which channel (R/G/B/A) to read
     - Target Channel: Where to write it (R/G/B/A)

4. Click **"Save Template"**

Custom templates are saved to `user_templates.json` and persist between sessions.

### Deleting Custom Templates

1. Select the custom template from the dropdown
2. Click the **"Delete"** button
3. Confirm deletion

*Note: Built-in templates cannot be deleted.*

## Output Files

Output files are named following this pattern:
```
<BaseName>_<Resolution>_<OutputName>.png
```

Example:
```
T_Forest_Floor_wgxsded_4K_DR.png
T_Forest_Floor_wgxsded_4K_ND.png
```

## Troubleshooting

### "No complete texture sets found"
- Verify your EXR files follow the naming convention
- Ensure you have all required input files (D, N, ORDp for default templates)
- Check that files have the correct resolution prefix (8K, 4K, 2K, or 1K)

### OpenEXR import errors
- Make sure OpenEXR is properly installed on your system
- On Linux/Mac, install system OpenEXR libraries (see Prerequisites)
- Try reinstalling the Python OpenEXR package: `pip install --force-reinstall openexr`

### Port 5000 already in use
Edit `app.py` and change the port number:
```python
app.run(debug=False, host='0.0.0.0', port=5001)  # Change 5000 to another port
```

### Browser doesn't open automatically
Manually navigate to: `http://localhost:5000`

## Technical Details

### Channel Packing
The application reads individual channels from EXR files and combines them into RGBA PNG files. This reduces texture count and memory usage in Unreal Engine.

### Gamma Correction
- **Enabled**: Converts from linear to sRGB (gamma 2.2) - use for color/diffuse textures
- **Disabled**: Keeps data linear - use for normal maps, masks, and data textures

### File Processing
- Each texture set is identified by its unique ID
- All textures with matching IDs and resolutions are processed together
- Missing required files are reported in the logs
- Supports multiple texture sets in a single conversion

## Project Structure

```
ImageTextureConversion/
├── app.py                    # Flask web application
├── convert_textures.py       # Core conversion logic
├── templates/
│   └── index.html           # Web interface
├── user_templates.json      # Custom user templates (auto-created)
├── start.bat               # Windows launcher
└── README.md              # This file
```

## License

<a href="https://github.com/neXib/ZC-TextureConversionPacker">ZC-TextureConversionPacker</a> © 2026 by <a href="https://www.zeticeta.com">ZetiCeta</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a><img src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;"><img src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;">

## Support

For issues, questions, or contributions, please submit pull request or add issues.
