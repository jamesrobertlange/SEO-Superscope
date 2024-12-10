# SEO Content Analysis Tool

## Overview
A Streamlit-based web application for analyzing SEO content across different page types. This tool helps identify patterns, duplicates, and n-gram frequencies in titles and meta descriptions, making it easier to maintain content consistency and identify optimization opportunities.

## Features
- Interactive web interface built with Streamlit
- Support for CSV and TSV file formats
- Comprehensive duplicate content analysis
- N-gram analysis (bigrams, trigrams, 4-grams)
- Page type breakdown and statistics
- Downloadable analysis reports
- Real-time progress tracking
- Interactive data visualization
- Configurable processing parameters

## Requirements
- Python 3.8+
- Required packages:
  ```
  streamlit>=1.28.0
  pandas>=1.5.0
  nltk>=3.8.1
  tqdm>=4.65.0
  ```

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

3. Upload your CSV/TSV file containing the following required columns:
   - Full URL
   - pagetype
   - Title
   - Meta Description

4. Configure analysis settings in the sidebar:
   - Select the appropriate file delimiter
   - Adjust chunk size if needed

5. Click "Run Analysis" to start processing

## Input File Requirements

Your input file should be a CSV or TSV with the following columns:
- `Full URL`: The complete URL of the page
- `pagetype`: The category or type of the page
- `Title`: The page's title tag content
- `Meta Description`: The page's meta description content

Example format:
```csv
Full URL,pagetype,Title,Meta Description
https://example.com/page1,blog,"First Blog Post","This is a description of the first blog post"
https://example.com/page2,product,"Product Name","Product description here"
```

## Analysis Features

### Title Analysis
- Identifies duplicate titles across all pages
- Groups duplicates by page type
- Calculates duplication rates
- Provides detailed duplicate instances

### Meta Description Analysis
- Finds duplicate meta descriptions
- Groups by page type
- Shows duplication patterns
- Lists affected URLs

### N-gram Analysis
- Analyzes frequent word patterns
- Supports 2-gram, 3-gram, and 4-gram analysis
- Breaks down patterns by page type
- Shows frequency counts

### Export Options
- CSV exports for all analyses
- Comprehensive summary report
- Detailed breakdown by page type
- N-gram frequency reports

## Output Files

The tool generates several downloadable files:
1. Duplicate Analysis:
   - `title_duplicate_rollup.csv`
   - `meta_description_duplicate_rollup.csv`
   - `title_pagetype_summary.csv`
   - `meta_description_pagetype_summary.csv`

2. N-gram Analysis:
   - `title_2gram_analysis.csv`
   - `title_3gram_analysis.csv`
   - `title_4gram_analysis.csv`
   - `meta_description_2gram_analysis.csv`
   - `meta_description_3gram_analysis.csv`
   - `meta_description_4gram_analysis.csv`

3. Summary:
   - `analysis_summary.txt`

## Performance Tips

- For large files (>1GB), increase the chunk size in the sidebar
- Close other memory-intensive applications when processing large datasets
- Use a machine with at least 8GB RAM for optimal performance

## Error Handling

The tool includes comprehensive error handling for:
- Missing or invalid columns
- File format issues
- Memory limitations
- Processing errors

If you encounter errors:
1. Check your input file format
2. Verify required columns are present
3. Adjust chunk size if needed
4. Ensure sufficient system resources

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For bugs, questions, and discussions, please use the GitHub Issues page.

## Acknowledgments

- Built with Streamlit
- Uses NLTK for natural language processing
- Powered by pandas for data analysis