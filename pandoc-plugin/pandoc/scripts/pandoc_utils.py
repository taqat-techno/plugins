#!/usr/bin/env python3
"""
Pandoc Utilities for Claude Code Plugin
========================================

Helper functions for Pandoc document conversion operations.

Author: TaqaTechno
Version: 1.0.0
License: MIT
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# FORMAT MAPPINGS
# ============================================================================

# Map file extensions to Pandoc input formats
INPUT_FORMAT_MAP = {
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.txt': 'plain',
    '.text': 'plain',
    '.html': 'html',
    '.htm': 'html',
    '.xhtml': 'html',
    '.docx': 'docx',
    '.doc': 'docx',  # Note: .doc requires conversion first
    '.odt': 'odt',
    '.rtf': 'rtf',
    '.tex': 'latex',
    '.latex': 'latex',
    '.rst': 'rst',
    '.rest': 'rst',
    '.org': 'org',
    '.adoc': 'asciidoc',
    '.asciidoc': 'asciidoc',
    '.epub': 'epub',
    '.ipynb': 'ipynb',
    '.csv': 'csv',
    '.tsv': 'tsv',
    '.json': 'json',
    '.xml': 'docbook',
    '.wiki': 'mediawiki',
    '.jira': 'jira',
}

# Map file extensions to Pandoc output formats
OUTPUT_FORMAT_MAP = {
    '.pdf': 'pdf',
    '.docx': 'docx',
    '.odt': 'odt',
    '.rtf': 'rtf',
    '.html': 'html',
    '.htm': 'html',
    '.epub': 'epub',
    '.epub3': 'epub3',
    '.tex': 'latex',
    '.latex': 'latex',
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.rst': 'rst',
    '.org': 'org',
    '.adoc': 'asciidoc',
    '.txt': 'plain',
    '.pptx': 'pptx',
    '.xml': 'docbook',
    '.json': 'json',
}


# ============================================================================
# PANDOC INSTALLATION
# ============================================================================

def check_pandoc_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if Pandoc is installed and return version.

    Returns:
        Tuple of (is_installed, version_string)
    """
    try:
        result = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split('\n')[0]
            version = version_line.replace('pandoc ', '').strip()
            return True, version
        return False, None
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None


def check_latex_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if LaTeX is installed (required for PDF generation).

    Returns:
        Tuple of (is_installed, engine_name)
    """
    engines = ['pdflatex', 'xelatex', 'lualatex']

    for engine in engines:
        try:
            result = subprocess.run(
                [engine, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, engine
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

    return False, None


def get_pandoc_info() -> Dict:
    """
    Get comprehensive Pandoc installation information.

    Returns:
        Dictionary with installation details
    """
    info = {
        'pandoc_installed': False,
        'pandoc_version': None,
        'pandoc_path': None,
        'latex_installed': False,
        'latex_engine': None,
        'input_formats': [],
        'output_formats': [],
    }

    # Check Pandoc
    installed, version = check_pandoc_installed()
    info['pandoc_installed'] = installed
    info['pandoc_version'] = version

    if installed:
        # Get path
        info['pandoc_path'] = shutil.which('pandoc')

        # Get formats
        try:
            result = subprocess.run(
                ['pandoc', '--list-input-formats'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info['input_formats'] = result.stdout.strip().split('\n')
        except subprocess.SubprocessError:
            pass

        try:
            result = subprocess.run(
                ['pandoc', '--list-output-formats'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info['output_formats'] = result.stdout.strip().split('\n')
        except subprocess.SubprocessError:
            pass

    # Check LaTeX
    latex_installed, engine = check_latex_installed()
    info['latex_installed'] = latex_installed
    info['latex_engine'] = engine

    return info


# ============================================================================
# FORMAT DETECTION
# ============================================================================

def detect_input_format(file_path: str) -> Optional[str]:
    """
    Detect input format from file extension.

    Args:
        file_path: Path to input file

    Returns:
        Pandoc format name or None
    """
    ext = Path(file_path).suffix.lower()
    return INPUT_FORMAT_MAP.get(ext)


def detect_output_format(file_path: str) -> Optional[str]:
    """
    Detect output format from file extension.

    Args:
        file_path: Path to output file

    Returns:
        Pandoc format name or None
    """
    ext = Path(file_path).suffix.lower()
    return OUTPUT_FORMAT_MAP.get(ext)


def suggest_output_formats(input_format: str) -> List[str]:
    """
    Suggest appropriate output formats for a given input format.

    Args:
        input_format: Pandoc input format name

    Returns:
        List of suggested output formats
    """
    # Common recommendations based on input
    suggestions = {
        'markdown': ['pdf', 'docx', 'html', 'epub', 'latex'],
        'docx': ['markdown', 'html', 'pdf', 'latex', 'plain'],
        'html': ['markdown', 'docx', 'pdf', 'epub', 'plain'],
        'latex': ['pdf', 'docx', 'html', 'markdown'],
        'rst': ['html', 'pdf', 'docx', 'markdown'],
        'org': ['html', 'pdf', 'docx', 'markdown'],
        'epub': ['html', 'markdown', 'docx'],
        'ipynb': ['markdown', 'html', 'pdf'],
    }

    return suggestions.get(input_format, ['pdf', 'docx', 'html', 'markdown'])


# ============================================================================
# COMMAND BUILDING
# ============================================================================

def build_conversion_command(
    input_file: str,
    output_file: str,
    input_format: Optional[str] = None,
    output_format: Optional[str] = None,
    options: Optional[Dict] = None
) -> List[str]:
    """
    Build a Pandoc conversion command.

    Args:
        input_file: Path to input file
        output_file: Path to output file
        input_format: Explicit input format (auto-detected if None)
        output_format: Explicit output format (auto-detected if None)
        options: Additional options dictionary

    Returns:
        Command as list of strings
    """
    cmd = ['pandoc']

    # Input format
    if input_format:
        cmd.extend(['-f', input_format])

    # Output format
    if output_format:
        cmd.extend(['-t', output_format])

    # Process options
    if options:
        if options.get('standalone', False):
            cmd.append('-s')

        if options.get('toc', False):
            cmd.append('--toc')
            toc_depth = options.get('toc_depth', 3)
            cmd.append(f'--toc-depth={toc_depth}')

        if options.get('number_sections', False):
            cmd.append('-N')

        if options.get('css'):
            cmd.extend(['-c', options['css']])

        if options.get('template'):
            cmd.extend(['--template', options['template']])

        if options.get('bibliography'):
            cmd.append('--citeproc')
            cmd.extend(['--bibliography', options['bibliography']])

        if options.get('csl'):
            cmd.extend(['--csl', options['csl']])

        if options.get('pdf_engine'):
            cmd.extend(['--pdf-engine', options['pdf_engine']])

        if options.get('highlight_style'):
            cmd.extend(['--highlight-style', options['highlight_style']])

        if options.get('embed_resources', False):
            cmd.append('--embed-resources')

        if options.get('extract_media'):
            cmd.extend(['--extract-media', options['extract_media']])

        # Variables
        for key, value in options.get('variables', {}).items():
            cmd.extend(['-V', f'{key}={value}'])

        # Metadata
        for key, value in options.get('metadata', {}).items():
            cmd.extend(['--metadata', f'{key}={value}'])

    # Input and output files
    cmd.append(input_file)
    cmd.extend(['-o', output_file])

    return cmd


def build_pdf_command(
    input_file: str,
    output_file: str,
    options: Optional[Dict] = None
) -> List[str]:
    """Build command for PDF generation."""
    default_options = {
        'standalone': True,
        'pdf_engine': 'pdflatex',
        'variables': {
            'geometry:margin': '1in',
            'fontsize': '12pt',
        }
    }

    if options:
        default_options.update(options)

    return build_conversion_command(
        input_file, output_file,
        output_format='pdf',
        options=default_options
    )


def build_slides_command(
    input_file: str,
    output_file: str,
    format: str = 'revealjs',
    theme: str = 'black',
    options: Optional[Dict] = None
) -> List[str]:
    """Build command for slide generation."""
    cmd = ['pandoc', '-t', format, '-s']

    if format == 'revealjs':
        cmd.extend(['-V', f'theme={theme}'])
        cmd.extend(['-V', 'controls=true'])
        cmd.extend(['-V', 'progress=true'])
    elif format == 'beamer':
        cmd.extend(['-V', f'theme:{theme}'])

    if options:
        for key, value in options.items():
            cmd.extend(['-V', f'{key}={value}'])

    cmd.append(input_file)
    cmd.extend(['-o', output_file])

    return cmd


# ============================================================================
# EXECUTION
# ============================================================================

def run_pandoc(
    cmd: List[str],
    cwd: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Run a Pandoc command.

    Args:
        cmd: Command as list of strings
        cwd: Working directory

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300  # 5 minute timeout
        )

        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )
    except subprocess.TimeoutExpired:
        return False, '', 'Conversion timed out after 5 minutes'
    except Exception as e:
        return False, '', str(e)


def convert_document(
    input_file: str,
    output_file: str,
    **kwargs
) -> Dict:
    """
    High-level document conversion function.

    Args:
        input_file: Path to input file
        output_file: Path to output file
        **kwargs: Additional options

    Returns:
        Result dictionary with success status and details
    """
    result = {
        'success': False,
        'input_file': input_file,
        'output_file': output_file,
        'command': [],
        'stdout': '',
        'stderr': '',
        'error': None,
    }

    # Check Pandoc installation
    if not check_pandoc_installed()[0]:
        result['error'] = 'Pandoc is not installed'
        return result

    # Check input file exists
    if not Path(input_file).exists():
        result['error'] = f'Input file not found: {input_file}'
        return result

    # Build command
    cmd = build_conversion_command(input_file, output_file, options=kwargs)
    result['command'] = cmd

    # Execute
    success, stdout, stderr = run_pandoc(cmd)
    result['success'] = success
    result['stdout'] = stdout
    result['stderr'] = stderr

    if not success:
        result['error'] = stderr or 'Conversion failed'

    return result


# ============================================================================
# UTILITIES
# ============================================================================

def get_file_info(file_path: str) -> Dict:
    """Get information about a file."""
    path = Path(file_path)

    if not path.exists():
        return {'exists': False}

    return {
        'exists': True,
        'name': path.name,
        'extension': path.suffix,
        'size_bytes': path.stat().st_size,
        'size_kb': round(path.stat().st_size / 1024, 2),
        'format': detect_input_format(file_path),
    }


def format_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f} MB'


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI interface for utilities."""
    if len(sys.argv) < 2:
        print('Usage: pandoc_utils.py <command> [args]')
        print('Commands:')
        print('  check     - Check Pandoc installation')
        print('  info      - Get detailed Pandoc info')
        print('  formats   - List supported formats')
        print('  detect    - Detect file format')
        return

    command = sys.argv[1]

    if command == 'check':
        installed, version = check_pandoc_installed()
        if installed:
            print(f'Pandoc {version} is installed')
        else:
            print('Pandoc is NOT installed')

    elif command == 'info':
        info = get_pandoc_info()
        print(json.dumps(info, indent=2))

    elif command == 'formats':
        info = get_pandoc_info()
        print('Input Formats:')
        for fmt in info['input_formats'][:20]:
            print(f'  {fmt}')
        print(f'  ... and {len(info["input_formats"]) - 20} more')
        print('\nOutput Formats:')
        for fmt in info['output_formats'][:20]:
            print(f'  {fmt}')
        print(f'  ... and {len(info["output_formats"]) - 20} more')

    elif command == 'detect':
        if len(sys.argv) < 3:
            print('Usage: pandoc_utils.py detect <file>')
            return
        file_path = sys.argv[2]
        format = detect_input_format(file_path)
        print(f'Detected format: {format or "unknown"}')

    else:
        print(f'Unknown command: {command}')


if __name__ == '__main__':
    main()
