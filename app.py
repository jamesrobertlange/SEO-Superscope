import streamlit as st
import pandas as pd
import os
from pathlib import Path
from collections import Counter
from nltk.util import ngrams
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
import re
from datetime import datetime
import base64
import io

# Page config
st.set_page_config(
    page_title="SEO Content Analysis Tool",
    page_icon="📊",
    layout="wide"
)
# Download required NLTK data at startup
@st.cache_resource
def download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

# Download NLTK data before the app starts
download_nltk_data()

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'results' not in st.session_state:
    st.session_state.results = {}


def preprocess_text(text):
    """Clean and tokenize text for n-gram analysis."""
    if pd.isna(text) or not isinstance(text, str):
        return []

    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t not in stop_words]
    return tokens


def extract_ngrams(tokens, n):
    """Extract n-grams from tokenized text."""
    n_grams = list(ngrams(tokens, n))
    return [' '.join(gram) for gram in n_grams]


def create_duplicate_rollup(df, content_type):
    """Create a comprehensive rollup of all duplicates across page types."""
    duplicated_mask = df.duplicated(subset=[content_type], keep=False)
    duplicates_df = df[duplicated_mask].copy()

    if duplicates_df.empty:
        return None, None

    rollup = duplicates_df.groupby(content_type).agg({
        'Full URL': list,
        'pagetype': list,
        'Meta Description' if content_type == 'Title' else 'Title': list
    }).reset_index()

    rollup['Duplicate_Count'] = rollup['Full URL'].apply(len)
    rollup['Unique_Pagetypes'] = rollup['pagetype'].apply(lambda x: len(set(x)))
    rollup['Pagetype_List'] = rollup['pagetype'].apply(lambda x: ', '.join(sorted(set(x))))
    rollup['URLs'] = rollup['Full URL'].apply(lambda x: '\n'.join(sorted(x)))

    if content_type == 'Title':
        rollup['Meta_Descriptions'] = rollup['Meta Description'].apply(
            lambda x: '\n'.join(sorted(set(str(desc) for desc in x)))
        )
        columns = [
            'Title', 'Duplicate_Count', 'Unique_Pagetypes', 'Pagetype_List',
            'Meta_Descriptions', 'URLs'
        ]
    else:
        rollup['Titles'] = rollup['Title'].apply(
            lambda x: '\n'.join(sorted(set(str(title) for title in x)))
        )
        columns = [
            'Meta Description', 'Duplicate_Count', 'Unique_Pagetypes', 'Pagetype_List',
            'Titles', 'URLs'
        ]

    rollup = rollup[columns].sort_values('Duplicate_Count', ascending=False)

    detailed_rows = []
    for _, row in duplicates_df.iterrows():
        detailed_rows.append({
            'Content': row[content_type],
            'URL': row['Full URL'],
            'Pagetype': row['pagetype'],
            'Other_Content': row['Meta Description'] if content_type == 'Title' else row['Title']
        })

    detailed_df = pd.DataFrame(detailed_rows)

    return rollup, detailed_df


def analyze_content(df, content_type, include_ngrams=True, ngram_sizes=[2, 3, 4]):
    """Analyze content (titles or meta descriptions) across page types."""
    rollup_df, detailed_df = create_duplicate_rollup(df, content_type)

    duplicates = df.groupby(content_type).agg({
        'Full URL': 'count',
        'pagetype': lambda x: ', '.join(set(x))
    }).reset_index()
    duplicates.columns = [content_type, 'Duplicate_Count', 'Pagetypes']
    duplicates = duplicates.sort_values('Duplicate_Count', ascending=False)

    pagetype_summary = df.groupby('pagetype').agg({
        'Full URL': 'count',
        content_type: lambda x: x.duplicated().sum()
    }).reset_index()
    pagetype_summary.columns = [
        'Pagetype', 'Total_URLs', f'Duplicate_{content_type}s'
    ]
    pagetype_summary['Duplication_Rate'] = (
        pagetype_summary[f'Duplicate_{content_type}s'] /
        pagetype_summary['Total_URLs'] * 100
    ).round(2)

    duplicate_analysis_by_pagetype = {}
    for pagetype in df['pagetype'].unique():
        pagetype_data = df[df['pagetype'] == pagetype]
        duplicates_in_pagetype = pagetype_data[
            pagetype_data.duplicated(subset=[content_type], keep=False)
        ]
        if not duplicates_in_pagetype.empty:
            duplicate_analysis_by_pagetype[pagetype] = duplicates_in_pagetype

    # N-gram analysis
    ngram_analyses = {}

    # Only perform n-gram analysis if requested
    if include_ngrams and len(ngram_sizes) > 0:
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            with st.spinner('Downloading required NLTK data...'):
                nltk.download('punkt')
                nltk.download('stopwords')

        for n in ngram_sizes:
            ngram_counts_by_pagetype = {}

            for pagetype in df['pagetype'].unique():
                content = df[df['pagetype'] == pagetype][content_type]

                all_ngrams = []
                for text in content:
                    tokens = preprocess_text(text)
                    if tokens:
                        text_ngrams = extract_ngrams(tokens, n)
                        all_ngrams.extend(text_ngrams)

                ngram_counts = Counter(all_ngrams)
                frequent_ngrams = {
                    gram: count for gram, count in ngram_counts.items()
                    if count > 1
                }

                if frequent_ngrams:
                    ngram_counts_by_pagetype[pagetype] = frequent_ngrams

            rows = []
            for pagetype, ngram_counts in ngram_counts_by_pagetype.items():
                for ngram, count in ngram_counts.items():
                    rows.append({
                        'pagetype': pagetype,
                        'ngram': ngram,
                        'frequency': count
                    })

            if rows:
                ngram_df = pd.DataFrame(rows)
                ngram_df = ngram_df.sort_values(
                    ['pagetype', 'frequency'],
                    ascending=[True, False]
                )
                ngram_analyses[n] = ngram_df

    return (
        duplicates,
        pagetype_summary,
        duplicate_analysis_by_pagetype,
        ngram_analyses,
        rollup_df,
        detailed_df
    )


def get_csv_download_link(df, filename):
    """Generate a download link for a dataframe."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = (
        f'<a href="data:file/csv;base64,{b64}" '
        f'download="{filename}">Download {filename}</a>'
    )
    return href

def main():
    st.title("SEO Content Analysis Tool")
    st.write("""
    This tool analyzes SEO content (titles and meta descriptions) across different page types,
    identifying patterns, duplicates, and n-gram frequencies.
    """)

    # File upload
    uploaded_file = st.file_uploader(
        "Upload your CSV/TSV file",
        type=['csv', 'tsv'],
        help="File should contain columns: Full URL, pagetype, Title, Meta Description"
    )

    if uploaded_file:
        # Configuration sidebar
        st.sidebar.header("Analysis Configuration")

        # File configuration
        st.sidebar.subheader("File Settings")
        delimiter = st.sidebar.selectbox(
            "File delimiter",
            options=[',', '\t', ';', '|'],
            index=0,
            format_func=lambda x: 'Tab' if x == '\t' else x
        )

        chunk_size = st.sidebar.number_input(
            "Chunk size",
            min_value=1000,
            max_value=1000000,
            value=100000,
            step=10000,
            help="Larger chunks process faster but use more memory"
        )

        # Analysis configuration
        st.sidebar.subheader("Analysis Options")
        analysis_type = st.sidebar.multiselect(
            "Select content to analyze",
            options=["Titles", "Meta Descriptions"],
            default=["Titles", "Meta Descriptions"],
            help="Choose which content types to analyze"
        )

        include_ngrams = st.sidebar.checkbox(
            "Include N-gram Analysis",
            value=True,
            help="Enable to analyze word patterns (may increase processing time)"
        )

        ngram_sizes = []
        if include_ngrams:
            ngram_sizes = st.sidebar.multiselect(
                "Select N-gram sizes",
                options=["Bigrams (2)", "Trigrams (3)", "4-grams (4)"],
                default=["Bigrams (2)", "Trigrams (3)", "4-grams (4)"],
                help="Choose which n-gram sizes to analyze"
            )
            
        try:
            with st.spinner("Reading and processing file..."):
                df = pd.read_csv(uploaded_file, sep=delimiter)

                # Verify required columns
                required_columns = {'Full URL', 'pagetype', 'Title', 'Meta Description'}
                missing_columns = required_columns - set(df.columns)

                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    st.write("Available columns:", ', '.join(df.columns))
                    return

                # Display basic file info
                st.subheader("File Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total URLs", f"{len(df):,}")
                with col2:
                    st.metric("Unique URLs", f"{df['Full URL'].nunique():,}")
                with col3:
                    st.metric("Page Types", f"{df['pagetype'].nunique():,}")

                # Analyze button
                if st.button("Run Analysis"):
                    with st.spinner("Analyzing content..."):
                        title_results = None
                        meta_results = None

                        # Extract numbers from n-gram selections
                        selected_sizes = []
                        if include_ngrams and ngram_sizes:
                            for size_option in ngram_sizes:
                                # Extract the number from strings like "Bigrams (2)"
                                number = re.search(r'\((\d+)\)', size_option)
                                if number:
                                    selected_sizes.append(int(number.group(1)))

                        # Title analysis
                        if "Titles" in analysis_type:
                            st.info("Analyzing titles...")
                            title_results = analyze_content(
                                df,
                                'Title',
                                include_ngrams=include_ngrams,
                                ngram_sizes=selected_sizes
                            )

                        # Meta description analysis
                        if "Meta Descriptions" in analysis_type:
                            st.info("Analyzing meta descriptions...")
                            meta_results = analyze_content(
                                df,
                                'Meta Description',
                                include_ngrams=include_ngrams,
                                ngram_sizes=selected_sizes
                            )

                        # Store results in session state
                        st.session_state.results = {
                            'title': title_results,
                            'meta': meta_results
                        }
                        st.session_state.analysis_complete = True

                        st.success("Analysis complete!")
                        st.experimental_rerun()

                # Display results if analysis is complete
                if st.session_state.analysis_complete:
                    title_results = st.session_state.results['title']
                    meta_results = st.session_state.results['meta']

                    st.header("Analysis Results")

                    # Create dynamic tabs based on selected analyses
                    tab_options = []
                    if "Titles" in analysis_type:
                        tab_options.append("Title Analysis")
                    if "Meta Descriptions" in analysis_type:
                        tab_options.append("Meta Description Analysis")
                    if include_ngrams and len(ngram_sizes) > 0:
                        tab_options.append("N-gram Analysis")
                    tab_options.append("Export Results")

                    tabs = st.tabs(tab_options)
                    
                    tab_index = 0  # Keep track of current tab index

                    # Title Analysis Tab
                    if "Titles" in analysis_type:
                        with tabs[tab_index]:
                            st.subheader("Title Duplicate Analysis")
                            if title_results[4] is not None:  # title_rollup
                                st.dataframe(title_results[4])
                                st.markdown(
                                    get_csv_download_link(
                                        title_results[4],
                                        "title_duplicate_rollup.csv"
                                    ),
                                    unsafe_allow_html=True
                                )

                            st.subheader("Title Duplication by Page Type")
                            st.dataframe(title_results[1])  # title_pagetype_summary
                        tab_index += 1

                    # Meta Description Analysis Tab
                    if "Meta Descriptions" in analysis_type and meta_results is not None:
                        with tabs[tab_index]:
                            st.subheader("Meta Description Duplicate Analysis")
                            if meta_results[4] is not None:  # meta_rollup
                                st.dataframe(meta_results[4])
                                st.markdown(
                                    get_csv_download_link(
                                        meta_results[4],
                                        "meta_description_duplicate_rollup.csv"
                                    ),
                                    unsafe_allow_html=True
                                )

                            st.subheader("Meta Description Duplication by Page Type")
                            st.dataframe(meta_results[1])  # meta_pagetype_summary
                        tab_index += 1

                    # N-gram Analysis Tab
                    if include_ngrams and len(ngram_sizes) > 0:
                        with tabs[tab_index]:
                            if "Titles" in analysis_type and title_results is not None:
                                st.subheader("Title N-grams")
                                gram_tabs = st.tabs(["Bigrams", "Trigrams", "4-grams"])
                                for i, gram_tab in enumerate(gram_tabs):
                                    with gram_tab:
                                        n = i + 2
                                        if title_results[3] is not None and n in title_results[3]:
                                            st.dataframe(title_results[3][n])

                            if "Meta Descriptions" in analysis_type and meta_results is not None:
                                st.subheader("Meta Description N-grams")
                                gram_tabs = st.tabs(["Bigrams", "Trigrams", "4-grams"])
                                for i, gram_tab in enumerate(gram_tabs):
                                    with gram_tab:
                                        n = i + 2
                                        if meta_results[3] is not None and n in meta_results[3]:
                                            st.dataframe(meta_results[3][n])
                        tab_index += 1

                    # Export Results Tab
                    with tabs[tab_index]:
                        st.subheader("Download Analysis Results")

                        # Create download buttons for all available analysis files
                        if "Titles" in analysis_type and title_results[4] is not None:
                            st.markdown(
                                get_csv_download_link(
                                    title_results[4],
                                    "title_duplicate_rollup.csv"
                                ),
                                unsafe_allow_html=True
                            )
                            st.markdown(
                                get_csv_download_link(
                                    title_results[1],
                                    "title_pagetype_summary.csv"
                                ),
                                unsafe_allow_html=True
                            )

                        if "Meta Descriptions" in analysis_type and meta_results is not None:
                            if meta_results[4] is not None:
                                st.markdown(
                                    get_csv_download_link(
                                        meta_results[4],
                                        "meta_description_duplicate_rollup.csv"
                                    ),
                                    unsafe_allow_html=True
                                )
                            st.markdown(
                                get_csv_download_link(
                                    meta_results[1],
                                    "meta_description_pagetype_summary.csv"
                                ),
                                unsafe_allow_html=True
                            )

                        # N-gram downloads (only if n-gram analysis was performed)
                        if include_ngrams and len(ngram_sizes) > 0:
                            st.subheader("N-gram Analysis Downloads")
                            for n in [2, 3, 4]:
                                if "Titles" in analysis_type and title_results[3] is not None and n in title_results[3]:
                                    st.markdown(
                                        get_csv_download_link(
                                            title_results[3][n],
                                            f"title_{n}gram_analysis.csv"
                                        ),
                                        unsafe_allow_html=True
                                    )
                                if "Meta Descriptions" in analysis_type and meta_results is not None and meta_results[3] is not None and n in meta_results[3]:
                                    st.markdown(
                                        get_csv_download_link(
                                            meta_results[3][n],
                                            f"meta_description_{n}gram_analysis.csv"
                                        ),
                                        unsafe_allow_html=True
                                    )

                        # Generate summary report
                        st.subheader("Summary Report")
                        summary_text = f"""SEO Content Analysis Summary Report
=================================

Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Statistics
-----------------
Total URLs analyzed: {len(df):,}
Unique URLs: {df['Full URL'].nunique():,}
Total page types: {df['pagetype'].nunique():,}
"""
                        if "Titles" in analysis_type:
                            summary_text += f"""
Title Analysis
-------------
Total titles: {len(df):,}
Unique titles: {df['Title'].nunique():,}
Duplicate titles: {len(df[df.duplicated(subset=['Title'], keep=False)]):,}
"""
                            if title_results[4] is not None:
                                summary_text += (
                                    f"Number of unique duplicate titles: {len(title_results[4]):,}\n"
                                    f"Most repeated title: {title_results[4].iloc[0]['Duplicate_Count']:,} occurrences\n"
                                )

                        if "Meta Descriptions" in analysis_type:
                            summary_text += f"""
Meta Description Analysis
------------------------
Total meta descriptions: {len(df):,}
Unique meta descriptions: {df['Meta Description'].nunique():,}
Duplicate meta descriptions: {len(df[df.duplicated(subset=['Meta Description'], keep=False)]):,}
"""
                            if meta_results[4] is not None:
                                summary_text += (
                                    f"Number of unique duplicate meta descriptions: {len(meta_results[4]):,}\n"
                                    f"Most repeated meta description: {meta_results[4].iloc[0]['Duplicate_Count']:,} occurrences\n"
                                )

                        summary_text += "\nAnalysis by Page Type\n--------------------\n"
                        for pagetype in sorted(df['pagetype'].unique()):
                            pagetype_data = df[df['pagetype'] == pagetype]
                            summary_text += f"\nPage Type: {pagetype}\n"
                            summary_text += f"Total URLs: {len(pagetype_data):,}\n"

                            if "Titles" in analysis_type:
                                title_dupes = len(pagetype_data[
                                    pagetype_data.duplicated(subset=['Title'], keep=False)
                                ])
                                summary_text += f"Duplicate Titles: {title_dupes:,} "
                                if title_dupes > 0:
                                    summary_text += f"({(title_dupes/len(pagetype_data)*100):.1f}%)\n"
                                else:
                                    summary_text += "\n"

                            if "Meta Descriptions" in analysis_type:
                                meta_dupes = len(pagetype_data[
                                    pagetype_data.duplicated(subset=['Meta Description'], keep=False)
                                ])
                                summary_text += f"Duplicate Meta Descriptions: {meta_dupes:,} "
                                if meta_dupes > 0:
                                    summary_text += f"({(meta_dupes/len(pagetype_data)*100):.1f}%)\n"
                                else:
                                    summary_text += "\n"

                        # Display and provide download for summary report
                        st.text_area("Summary Report", summary_text, height=400)
                        b64 = base64.b64encode(summary_text.encode()).decode()
                        st.markdown(
                            f'<a href="data:text/plain;base64,{b64}" '
                            f'download="analysis_summary.txt">Download Summary Report</a>',
                            unsafe_allow_html=True
                        )

        except Exception as e:
            import traceback
            import sys
            
            # Get the full traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            # Print to terminal/console
            print("\n=== Error Details ===")
            print("Exception type:", exc_type.__name__)
            print("Error message:", str(e))
            print("\nFull traceback:")
            traceback.print_tb(exc_traceback)
            print("==================\n")
            
            # Still show user-friendly message in UI
            st.error(f"Error processing file: {str(e)}")
            st.write("Please check your file format and delimiter settings.")
            
            # For debugging, you can also show the full traceback in the UI
            with st.expander("Show Debug Information"):
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
