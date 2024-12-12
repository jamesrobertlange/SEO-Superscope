# SEO Content SuperScope
(Streamlit Web Application Here: https://seo-superscope.streamlit.app/)

> ### 🚀 TL;DR
> A powerful content analysis tool that takes common SEO CSV data (Title Tags, Meta Descriptions, URLs) from common SEO tools (such as Screaming Frog, Sitebulb, Botify, ...) and identifies duplication and n-gram commonalities quickly.

This tool helps you:
- Find duplicate titles and meta descriptions across your site
- Analyze content patterns with n-gram analysis
- Generate comprehensive reports by page type
- Export detailed CSV reports for all findings

> **Quick Start:** Upload a CSV/TSV file with URLs, titles, and meta descriptions, map your columns, and click analyze!

**Please Note:** The Page Type segment is custom; if you have internal segments add them here. If you do not, you can select 'none' under the Page Type column selector.

---

## Overview
A powerful Streamlit-based web application for comprehensive SEO content analysis. This tool helps content teams and SEO professionals identify patterns, duplicates, and optimization opportunities in titles and meta descriptions across different page types, with an emphasis on content consistency and quality control.

## Important Notes

### Streamlit Web Limitations
- This is a web-based tool built with Streamlit, which means:
  - Data is processed in-memory and is not stored or retained between sessions
  - Large files (>1GB) may experience performance issues due to browser memory constraints
  - The interface automatically refreshes when making selections, which may cause brief loading states
  - Only one analysis can be run at a time
  - Session data is lost upon browser refresh
  - File upload size may be limited by your browser settings

## Roadmap

### Planned Features
- Automatic page type detection based on URL patterns and content analysis
- Advanced URL parsing and site section identification
- Indexability analysis and technical SEO metrics
- Custom export templates and reporting
- Advanced pattern matching and content classification
- Integration with common SEO tools and APIs


## Core Features

### File Processing
- Support for both CSV and TSV file formats
- Flexible column mapping for various data structures
- Intelligent column name detection for common SEO tools (Screaming Frog, etc.)
- Auto-detection of file delimiters

### Content Analysis
- Comprehensive duplicate content detection
    - Title duplication analysis
    - Meta description duplication analysis
    - Cross-page type duplicate detection
    - Handling of empty/null values
- N-gram analysis (configurable)
    - Bigrams (2-word phrases)
    - Trigrams (3-word phrases)
    - 4-grams (4-word phrases)
- Page type segmentation and statistics
- Content pattern recognition

### Data Visualization & Reporting
- Interactive data tables
- Real-time progress tracking
- Dynamic metric displays
- Downloadable analysis reports
- Complete content reference tables
- Page type breakdown statistics

### Export Capabilities
- Comprehensive ZIP export of all analyses
- Individual file downloads
- Multiple export formats (CSV, TXT)
- Detailed summary reports
- Cross-referenced duplicate reports

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/seo-content-analysis.git
cd seo-content-analysis
```

2. Create and activate a virtual environment (recommended):
```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the provided URL (typically http://localhost:8501)

3. Upload your data file:
   - Supported formats: CSV, TSV
   - Common SEO tool exports supported (Screaming Frog, etc.)
   - Flexible column mapping available

4. Configure analysis settings:
   - Select content types to analyze (Titles, Meta Descriptions)
   - Enable/disable N-gram analysis
   - Choose N-gram sizes
   - Adjust file processing settings

5. Run the analysis and explore results

## Data Requirements

### Required Data Fields
The tool supports flexible column mapping for the following required fields:
- URL (Accepts variations: Full URL, Address, Link, etc.)
- Title (Accepts variations: Page Title, Title Tag, SEO Title, etc.)
- Meta Description (Accepts variations: Description, Meta Desc, etc.)
- Page Type (Optional - Accepts variations: Template, Category, Content Type, etc.)

### Accepted File Formats
```
- CSV (comma-separated)
- TSV (tab-separated)
- Custom delimiters (|, ;)
```

## Analysis Features

### Title Analysis
- Complete duplicate title detection
- Cross-page type duplicate identification
- Empty/null value handling
- Title pattern analysis
- Page type segmentation
- Reference tables for all titles

### Meta Description Analysis
- Duplicate meta description detection
- Cross-page type analysis
- Empty/null value handling
- Pattern recognition
- Page type breakdown
- Complete meta description reference

### N-gram Analysis
- Configurable n-gram sizes
- Frequency analysis
- Pattern identification
- Cross-page type comparison
- Word combination analysis

### Page Type Analysis
- Content segmentation by page type
- Duplicate rates per page type
- Cross-page type patterns
- Page type content summaries

## Output Files

### Comprehensive Analysis Package (ZIP)
All analysis results are available as a single ZIP download containing:

1. Duplicate Analysis Files:
   - `title_duplicate_rollup.csv`
   - `meta_description_duplicate_rollup.csv`
   - `title_pagetype_summary.csv`
   - `meta_description_pagetype_summary.csv`

2. N-gram Analysis Files:
   - `title_2gram_analysis.csv`
   - `title_3gram_analysis.csv`
   - `title_4gram_analysis.csv`
   - `meta_description_2gram_analysis.csv`
   - `meta_description_3gram_analysis.csv`
   - `meta_description_4gram_analysis.csv`

3. Reference Files:
   - `title_reference.csv`
   - `meta_description_reference.csv`

4. Summary Reports:
   - `analysis_summary.txt`

### Individual Downloads
Each analysis component is also available as a separate download.

## Performance Optimization

### Resource Management
- Efficient memory handling for large datasets
- Progressive file processing
- Optimized duplicate detection algorithms
- Streamlined n-gram analysis

### Best Practices
- Close memory-intensive applications before processing
- Use recommended system specifications:
  - 8GB+ RAM
  - Modern multi-core processor
  - SSD storage for large files

## Error Handling

### Comprehensive Error Detection
- File format validation
- Column mapping verification
- Data type checking
- Memory monitoring
- Processing error capture

### Error Recovery
- Detailed error messages
- Debugging information
- Recovery suggestions
- Performance recommendations

## Interface Features

### Dynamic UI
- Responsive layout
- Progress indicators
- Interactive data tables
- Expandable sections
- Configurable analysis options

### Navigation
- Tab-based results viewing
- Collapsible sidebars
- Quick-access controls
- Reset functionality

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support:
- Submit issues via GitHub Issues
- Review existing issues for solutions
- Check documentation for guidance

## Acknowledgments

Built with:
- Streamlit for web interface
- Pandas for data processing
- Python standard library

Special thanks to all contributors and users who provide valuable feedback and suggestions.