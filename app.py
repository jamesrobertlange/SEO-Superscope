import streamlit as st
import pandas as pd
import os
from pathlib import Path
from collections import Counter
import re
import traceback
from datetime import datetime
import base64
import io

# Page config
st.set_page_config(
    page_title="SEO Content Analysis Tool",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state['analysis_complete'] = False

if 'results' not in st.session_state:
    st.session_state['results'] = {}

def preprocess_text(text):
    """Clean and tokenize text using regex instead of NLTK."""
    if pd.isna(text) or not isinstance(text, str):
        return []
    
    # Convert to lowercase and remove special characters
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    
    # Simple tokenization by splitting on whitespace
    tokens = text.split()
    
    # Basic English stop words list
    stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 
        'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
        'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how',
        'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'than', 'too', 'very', 'can', 'will', 'just'
    }
    
    # Remove stop words
    tokens = [t for t in tokens if t not in stop_words and len(t) > 1]
    return tokens

def extract_ngrams(tokens, n):
    """Extract n-grams from tokenized text."""
    if len(tokens) < n:
        return []
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

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

    if include_ngrams and len(ngram_sizes) > 0:
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

            if ngram_counts_by_pagetype:
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

def infer_column_mapping(columns):
    """Infer column mappings based on common patterns in column names."""
    patterns = {
        'url': ['url', 'link', 'address', 'location', 'full url', 'page url'],
        'title': ['title', 'page title', 'title tag', 'page title tag', 'seo title'],
        'meta_description': ['meta description', 'description', 'meta desc', 'metadescription', 'meta'],
        'pagetype': ['page type', 'pagetype', 'type', 'template', 'category', 'page category']
    }
    
    mapping = {}
    for col in columns:
        col_lower = col.lower()
        for field, pattern_list in patterns.items():
            if any(pattern in col_lower for pattern in pattern_list):
                mapping[field] = col
                break
    return mapping

def display_column_mapper(df):
    """Display column mapping interface and return the mapping."""
    st.subheader("Column Mapping")
    st.write("Please map your file columns to the required fields. The tool will try to automatically detect the correct mappings.")
    
    # Get columns from dataframe
    columns = list(df.columns)
    
    # Infer initial mapping
    inferred_mapping = infer_column_mapping(columns)
    
    # Create two columns for layout
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### Map Your Columns")
        mapping = {}
        
        # Create mapping interface for each required field
        required_fields = {
            'url': 'URL',
            'title': 'Title',
            'meta_description': 'Meta Description',
            'pagetype': 'Page Type'
        }
        
        for field, display_name in required_fields.items():
            default_value = inferred_mapping.get(field, '')
            mapping[field] = st.selectbox(
                f"Select column for {display_name}",
                options=[''] + columns,
                index=columns.index(default_value) + 1 if default_value in columns else 0,
                help=f"Select the column that contains your {display_name.lower()}"
            )
    
    with col2:
        st.markdown("### Preview")
        if all(mapping.values()):
            preview_df = df[list(mapping.values())].head(3)
            preview_df.columns = list(required_fields.values())
            st.dataframe(preview_df, use_container_width=True)
            
            # Show mapping summary
            st.markdown("### Mapping Summary")
            for field, display_name in required_fields.items():
                st.write(f"✓ {display_name}: `{mapping[field]}`")
    
    # Confirm mapping button
    if st.button("Confirm Column Mapping", type="primary"):
        if all(mapping.values()):
            # Create standardized column names
            column_standardization = {
                mapping['url']: 'Full URL',
                mapping['title']: 'Title',
                mapping['meta_description']: 'Meta Description',
                mapping['pagetype']: 'pagetype'
            }
            
            # Create mapped dataframe
            mapped_df = df.copy()
            mapped_df = mapped_df.rename(columns=column_standardization)
            
            return mapped_df
        else:
            st.error("Please map all required columns before proceeding.")
            return None
            
    return None

def generate_summary_report(df, title_results, meta_results):
    """Generate a comprehensive summary report of the analysis."""
    summary_text = f"""SEO Content Analysis Summary Report
=================================

Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Statistics
-----------------
Total URLs analyzed: {len(df):,}
Unique URLs: {df['Full URL'].nunique():,}
Total page types: {df['pagetype'].nunique():,}
"""
    if title_results:
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

    if meta_results:
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

        if title_results:
            title_dupes = len(pagetype_data[
                pagetype_data.duplicated(subset=['Title'], keep=False)
            ])
            summary_text += f"Duplicate Titles: {title_dupes:,} "
            if title_dupes > 0:
                summary_text += f"({(title_dupes/len(pagetype_data)*100):.1f}%)\n"
            else:
                summary_text += "\n"

        if meta_results:
            meta_dupes = len(pagetype_data[
                pagetype_data.duplicated(subset=['Meta Description'], keep=False)
            ])
            summary_text += f"Duplicate Meta Descriptions: {meta_dupes:,} "
            if meta_dupes > 0:
                summary_text += f"({(meta_dupes/len(pagetype_data)*100):.1f}%)\n"
            else:
                summary_text += "\n"

    return summary_text

def main():
    st.title("SEO Content Analysis Tool")
    st.write("""
    This tool analyzes SEO content (titles and meta descriptions) across different page types,
    identifying patterns, duplicates, and n-gram frequencies.
    """)

    # Initialize session state
    if 'mapped_df' not in st.session_state:
        st.session_state.mapped_df = None
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'results' not in st.session_state:
        st.session_state.results = {}

    # File upload
    uploaded_file = st.file_uploader(
        "Upload your CSV/TSV file",
        type=['csv', 'tsv'],
        help="File should contain columns for URL, Title, Meta Description, and Page Type"
    )

    if uploaded_file:
        try:
            # File configuration in sidebar
            st.sidebar.header("File Settings")
            delimiter = st.sidebar.selectbox(
                "File delimiter",
                options=[',', '\t', ';', '|'],
                index=0,
                format_func=lambda x: 'Tab' if x == '\t' else x
            )

            # Read the file
            df = pd.read_csv(uploaded_file, sep=delimiter)

            # If mapping hasn't been done yet, show mapping interface
            if st.session_state.mapped_df is None:
                mapped_df = display_column_mapper(df)
                if mapped_df is not None:
                    st.session_state.mapped_df = mapped_df
                    st.success("Column mapping confirmed! You can now proceed with the analysis.")
                    st.experimental_rerun()
                return

            # Use mapped DataFrame for analysis
            df = st.session_state.mapped_df

            # Display basic file info
            st.subheader("File Overview")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total URLs", f"{len(df):,}")
            with col2:
                st.metric("Unique URLs", f"{df['Full URL'].nunique():,}")
            with col3:
                st.metric("Page Types", f"{df['pagetype'].nunique():,}")

            # Analysis configuration
            st.sidebar.subheader("Analysis Options")
            analysis_type = st.sidebar.multiselect(
                "Select content to analyze",
                options=["Titles", "Meta Descriptions"],
                default=["Titles", "Meta Descriptions"],
                help="Choose which content types to analyze"
            )

            chunk_size = st.sidebar.number_input(
                "Chunk size",
                min_value=1000,
                max_value=1000000,
                value=100000,
                step=10000,
                help="Larger chunks process faster but use more memory"
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

            # Analyze button
            if st.button("Run Analysis", type="primary"):
                with st.spinner("Analyzing content..."):
                    title_results = None
                    meta_results = None

                    # Extract numbers from n-gram selections
                    selected_sizes = []
                    if include_ngrams and ngram_sizes:
                        for size_option in ngram_sizes:
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
                
                tab_index = 0

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
                        st.dataframe(title_results[1])
                    tab_index += 1

                # Meta Description Analysis Tab
                if "Meta Descriptions" in analysis_type and meta_results is not None:
                    with tabs[tab_index]:
                        st.subheader("Meta Description Duplicate Analysis")
                        if meta_results[4] is not None:
                            st.dataframe(meta_results[4])
                            st.markdown(
                                get_csv_download_link(
                                    meta_results[4],
                                    "meta_description_duplicate_rollup.csv"
                                ),
                                unsafe_allow_html=True
                            )

                        st.subheader("Meta Description Duplication by Page Type")
                        st.dataframe(meta_results[1])
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

                    # Generate and display summary report
                    st.subheader("Summary Report")
                    summary_text = generate_summary_report(df, title_results, meta_results)
                    st.text_area("Summary Report", summary_text, height=400)
                    b64 = base64.b64encode(summary_text.encode()).decode()
                    st.markdown(
                        f'<a href="data:text/plain;base64,{b64}" '
                        f'download="analysis_summary.txt">Download Summary Report</a>',
                        unsafe_allow_html=True
                    )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            with st.expander("Show Debug Information"):
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()