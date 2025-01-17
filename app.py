import streamlit as st
import pandas as pd
import os
from pathlib import Path
from collections import Counter
import re
from datetime import datetime
import base64
import io
from io import BytesIO
import traceback
import zipfile

# Page config
st.set_page_config(
    page_title="SEO Content SuperScope",
    page_icon="📊",
    layout="wide"
)

# Initialize ALL session state variables
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = True
if 'show_analysis' not in st.session_state:
    st.session_state.show_analysis = False
if 'mapped_df' not in st.session_state:
    st.session_state.mapped_df = None
if 'mapping_complete' not in st.session_state:
    st.session_state.mapping_complete = False
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'results' not in st.session_state:
    st.session_state.results = {}

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
    # Map the content type to the actual column name
    column_mapping = {
        'Title': 'title',
        'Meta Description': 'meta_description'
    }
    
    content_column = column_mapping.get(content_type, content_type)
    
    # Replace empty strings and pure whitespace with None for consistent handling
    df[content_column] = df[content_column].replace(r'^\s*$', None, regex=True)
    
    # Create duplicate rollup including nulls
    duplicates_df = df[df.duplicated(subset=[content_column], keep=False)].copy()
    
    # Handle case where all values are unique
    if duplicates_df.empty:
        return None, None, None, {}, None, None

    # Create rollup of duplicates
    rollup = duplicates_df.groupby(content_column, dropna=False).agg({
        'url': list,
        'pagetype': list,
        'meta_description' if content_column == 'title' else 'title': list
    }).reset_index()

    # Replace None with "[BLANK]" for display
    rollup[content_column] = rollup[content_column].fillna("[BLANK]")
    
    rollup['Duplicate_Count'] = rollup['url'].apply(len)
    rollup['Unique_Pagetypes'] = rollup['pagetype'].apply(lambda x: len(set(x)))
    rollup['Pagetype_List'] = rollup['pagetype'].apply(lambda x: ', '.join(sorted(set(x))))
    rollup['URLs'] = rollup['url'].apply(lambda x: '\n'.join(sorted(x)))

    if content_column == 'title':
        rollup['Meta_Descriptions'] = rollup['meta_description'].apply(
            lambda x: '\n'.join(sorted(set(str(desc) if desc is not None else "[BLANK]" for desc in x)))
        )
        columns = [
            content_column, 'Duplicate_Count', 'Unique_Pagetypes', 'Pagetype_List',
            'Meta_Descriptions', 'URLs'
        ]
    else:
        rollup['Titles'] = rollup['title'].apply(
            lambda x: '\n'.join(sorted(set(str(title) if title is not None else "[BLANK]" for title in x)))
        )
        columns = [
            content_column, 'Duplicate_Count', 'Unique_Pagetypes', 'Pagetype_List',
            'Titles', 'URLs'
        ]

    rollup = rollup[columns].sort_values('Duplicate_Count', ascending=False)

    # Create summary of duplicates
    duplicates = df.groupby(content_column, dropna=False).agg({
        'url': 'count',
        'pagetype': lambda x: ', '.join(set(x))
    }).reset_index()
    duplicates.columns = [content_column, 'Duplicate_Count', 'Pagetypes']
    duplicates[content_column] = duplicates[content_column].fillna("[BLANK]")
    duplicates = duplicates.sort_values('Duplicate_Count', ascending=False)

    # Create pagetype summary
    pagetype_summary = df.groupby('pagetype', dropna=False).agg({
        'url': 'count',
        content_column: lambda x: x.duplicated().sum()
    }).reset_index()
    pagetype_summary.columns = [
        'Pagetype', 'Total_URLs', f'Duplicate_{content_type}s'
    ]
    pagetype_summary['Pagetype'] = pagetype_summary['Pagetype'].fillna("[BLANK]")
    pagetype_summary['Duplication_Rate'] = (
        pagetype_summary[f'Duplicate_{content_type}s'] /
        pagetype_summary['Total_URLs'] * 100
    ).round(2)

    # Analyze duplicates by pagetype
    duplicate_analysis_by_pagetype = {}
    for pagetype in df['pagetype'].unique():
        pagetype_data = df[df['pagetype'] == pagetype]
        duplicates_in_pagetype = pagetype_data[
            pagetype_data.duplicated(subset=[content_column], keep=False)
        ]
        if not duplicates_in_pagetype.empty:
            duplicate_analysis_by_pagetype[pagetype] = duplicates_in_pagetype

    # N-gram analysis
    ngram_analyses = {}
    if include_ngrams and len(ngram_sizes) > 0:
        # Create a list of all tokens from all content
        all_tokens = []
        for text in df[content_column][df[content_column].notna()]:
            tokens = preprocess_text(str(text))
            all_tokens.extend(tokens)
            
        # Generate n-grams for each size
        for n in ngram_sizes:
            # Get all n-grams
            all_ngrams = []
            for tokens in [preprocess_text(str(text)) for text in df[content_column][df[content_column].notna()]]:
                ngrams = extract_ngrams(tokens, n)
                all_ngrams.extend(ngrams)
            
            # Count n-gram frequencies
            ngram_counts = Counter(all_ngrams)
            
            # Convert to DataFrame
            if ngram_counts:
                ngram_df = pd.DataFrame.from_dict(ngram_counts, orient='index', columns=['Count'])
                ngram_df.index.name = f'{n}-gram'
                ngram_df = ngram_df.reset_index()
                ngram_df = ngram_df.sort_values('Count', ascending=False)
                
                # Calculate percentage
                total_ngrams = ngram_df['Count'].sum()
                ngram_df['Percentage'] = (ngram_df['Count'] / total_ngrams * 100).round(2)
                
                # Store in analyses dictionary
                ngram_analyses[n] = ngram_df

    # Create detailed duplicate analysis
    detailed_rows = []
    for _, row in duplicates_df.iterrows():
        detailed_rows.append({
            'Content': row[content_column] if row[content_column] is not None else "[BLANK]",
            'URL': row['url'],
            'Pagetype': row['pagetype'],
            'Other_Content': row['meta_description'] if content_column == 'title' else row['title']
        })

    detailed_df = pd.DataFrame(detailed_rows)

    return (
        duplicates,
        pagetype_summary,
        duplicate_analysis_by_pagetype,
        ngram_analyses,
        rollup,
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
        'url': ['url', 'link', 'address', 'location', 'full url', 'page url', 'url encoded address'],
        'title': ['title', 'page title', 'title tag', 'page title tag', 'seo title', 'title 1'],
        'meta_description': ['meta description', 'description', 'meta desc', 'metadescription', 'meta', 'meta description 1'],
        'pagetype': ['page type', 'pagetype', 'type', 'template', 'category', 'page category', 'content type']
    }
    
    mapping = {}
    columns_lower = [col.lower() for col in columns]
    
    # Create a mapping from lowercase to original column names
    original_case = {col.lower(): col for col in columns}
    
    for field, pattern_list in patterns.items():
        # Try exact matches first
        for pattern in pattern_list:
            if pattern in columns_lower:
                mapping[field] = original_case[pattern]
                break
        
        # If no exact match, try partial matches
        if field not in mapping:
            for col in columns_lower:
                if any(pattern in col for pattern in pattern_list):
                    mapping[field] = original_case[col]
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
        
        # Define required fields and their properties
        required_fields = [
            ('url', 'URL', True),
            ('title', 'Title', True),
            ('meta_description', 'Meta Description', True),
            ('pagetype', 'Page Type', False)
        ]
        
        # Create mapping interface for each field
        for field, display_name, required in required_fields:
            default_value = inferred_mapping.get(field, '')
            help_text = f"Select the column that contains your {display_name.lower()}"
            
            if not required:
                help_text += " (optional)"
                # Special handling for pagetype - add 'None' option
                options = ['None'] + columns
                selected_index = 0  # Default to 'None'
                if default_value and default_value in columns:
                    selected_index = options.index(default_value)
            else:
                options = columns
                selected_index = options.index(default_value) if default_value in options else 0
            
            mapping[field] = st.selectbox(
                f"Select column for {display_name}",
                options=options,
                index=selected_index,
                help=help_text
            )
    
    with col2:
        st.markdown("### Preview")
        preview_columns = [v for k, v in mapping.items() 
                         if v and v != 'None']  # Exclude 'None' from preview
        if preview_columns:
            preview_df = df[preview_columns].head(3)
            st.dataframe(preview_df, use_container_width=True)
            
            st.markdown("### Mapping Summary")
            for field, display_name, required in required_fields:
                if mapping[field] and mapping[field] != 'None':
                    st.write(f"✓ {display_name}: `{mapping[field]}`")
                elif field == 'pagetype':
                    st.write("⚪ Page Type: Will use 'None' as default")
    
    # Confirm mapping button
    st.markdown('<div class="confirmation-button">', unsafe_allow_html=True)
    if st.button("Confirm Column Mapping", type="primary"):
        if all(v for k, v in mapping.items() if k != 'pagetype'):  # Check all required fields except pagetype
            try:
                # Create new DataFrame with mapped columns
                mapped_df = pd.DataFrame()
                
                # Add required columns
                mapped_df['url'] = df[mapping['url']]
                mapped_df['title'] = df[mapping['title']]
                mapped_df['meta_description'] = df[mapping['meta_description']]
                
                # Handle pagetype
                if mapping['pagetype'] and mapping['pagetype'] != 'None':
                    mapped_df['pagetype'] = df[mapping['pagetype']]
                else:
                    mapped_df['pagetype'] = 'None'  # Use 'None' as the default value
                
                # Final check for required columns
                required_columns = {'url', 'title', 'meta_description', 'pagetype'}
                if not all(col in mapped_df.columns for col in required_columns):
                    st.error("Column mapping failed. Please check your column selections.")
                    return None
                
                st.success("Column mapping successful!")
                return mapped_df
                
            except Exception as e:
                st.error(f"Error mapping columns: {str(e)}")
                return None
        else:
            st.error("Please map all required columns before proceeding.")
            return None        
    return None

    st.markdown('</div>', unsafe_allow_html=True)

def generate_summary_report(df, title_results, meta_results):
    """Generate a comprehensive summary report of the analysis with both counting methods."""
    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()
    
    # Verify required columns exist with normalized names
    required_columns = {'url', 'title', 'meta_description', 'pagetype'}
    if not all(col in df.columns for col in required_columns):
        missing_cols = required_columns - set(df.columns)
        return f"Error: Missing required columns in the dataset: {', '.join(missing_cols)}"
        
    summary_text = f"""SEO Content Analysis Summary Report
=================================

Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Statistics
-----------------
Total URLs analyzed: {len(df):,}
Unique URLs: {df['url'].nunique():,}
Total page types: {df['pagetype'].nunique():,}
"""

    # Title analysis
    if title_results and 'title' in df.columns:
        # Get total URLs involved in title duplication
        urls_with_duplicate_titles = len(df[df.duplicated(subset=['title'], keep=False)])
        # Get number of additional/repeated instances
        extra_title_instances = len(df[df.duplicated(subset=['title'], keep='first')])
        
        summary_text += f"""
Title Analysis
-------------
Total titles: {len(df):,}
Unique titles: {df['title'].nunique():,}

Duplicate Title Metrics:
• Total URLs with duplicate title issues: {urls_with_duplicate_titles:,} ({(urls_with_duplicate_titles/len(df)*100):.1f}% of all URLs)
• Additional instances only: {extra_title_instances:,} ({(extra_title_instances/len(df)*100):.1f}% of all URLs)
"""
        if title_results[4] is not None and not title_results[4].empty:
            title_col = 'title' if 'title' in title_results[4].columns else 'Title'
            summary_text += (
                f"Most duplicated title details:\n"
                f"• Title: {title_results[4].iloc[0][title_col]}\n"
                f"• Times used: {title_results[4].iloc[0]['Duplicate_Count']:,}\n"
                f"• Page Types: {title_results[4].iloc[0]['Pagetype_List']}\n"
            )

    # Meta description analysis
    if meta_results and 'meta_description' in df.columns:
        # Get total URLs involved in meta description duplication
        urls_with_duplicate_metas = len(df[df.duplicated(subset=['meta_description'], keep=False)])
        # Get number of additional/repeated instances
        extra_meta_instances = len(df[df.duplicated(subset=['meta_description'], keep='first')])
        
        summary_text += f"""
Meta Description Analysis
------------------------
Total meta descriptions: {len(df):,}
Unique meta descriptions: {df['meta_description'].nunique():,}

Duplicate Meta Description Metrics:
• Total URLs with duplicate meta description issues: {urls_with_duplicate_metas:,} ({(urls_with_duplicate_metas/len(df)*100):.1f}% of all URLs)
• Additional instances only: {extra_meta_instances:,} ({(extra_meta_instances/len(df)*100):.1f}% of all URLs)
"""
        if meta_results[4] is not None and not meta_results[4].empty:
            meta_col = 'meta_description' if 'meta_description' in meta_results[4].columns else 'Meta Description'
            summary_text += (
                f"Most duplicated meta description details:\n"
                f"• Meta Description: {meta_results[4].iloc[0][meta_col]}\n"
                f"• Times used: {meta_results[4].iloc[0]['Duplicate_Count']:,}\n"
                f"• Page Types: {meta_results[4].iloc[0]['Pagetype_List']}\n"
            )

    summary_text += "\nAnalysis by Page Type\n--------------------"
    
    for pagetype in sorted(df['pagetype'].unique()):
        pagetype_data = df[df['pagetype'] == pagetype]
        summary_text += f"\n\nPage Type: {pagetype}"
        summary_text += f"\nTotal URLs: {len(pagetype_data):,}"

        if title_results and 'title' in df.columns:
            # Get both counts for titles
            total_title_dupes = len(pagetype_data[
                pagetype_data.duplicated(subset=['title'], keep=False)
            ])
            extra_title_dupes = len(pagetype_data[
                pagetype_data.duplicated(subset=['title'], keep='first')
            ])
            
            dupe_rate = (total_title_dupes/len(pagetype_data)*100) if total_title_dupes > 0 else 0
            extra_rate = (extra_title_dupes/len(pagetype_data)*100) if extra_title_dupes > 0 else 0
            
            summary_text += f"""
Title Duplication:
• URLs with duplicate titles: {total_title_dupes:,} ({dupe_rate:.1f}% of page type)
• Additional instances only: {extra_title_dupes:,} ({extra_rate:.1f}% of page type)"""

        if meta_results and 'meta_description' in df.columns:
            # Get both counts for meta descriptions
            total_meta_dupes = len(pagetype_data[
                pagetype_data.duplicated(subset=['meta_description'], keep=False)
            ])
            extra_meta_dupes = len(pagetype_data[
                pagetype_data.duplicated(subset=['meta_description'], keep='first')
            ])
            
            dupe_rate = (total_meta_dupes/len(pagetype_data)*100) if total_meta_dupes > 0 else 0
            extra_rate = (extra_meta_dupes/len(pagetype_data)*100) if extra_meta_dupes > 0 else 0
            
            summary_text += f"""
Meta Description Duplication:
• URLs with duplicate meta descriptions issues: {total_meta_dupes:,} ({dupe_rate:.1f}% of page type)
• Additional instances only: {extra_meta_dupes:,} ({extra_rate:.1f}% of page type)"""

    return summary_text

def create_zip_download(files_dict):
    """Create a zip file containing multiple analysis files.
    
    Args:
        files_dict (dict): Dictionary with filenames as keys and DataFrames/strings as values
    """
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files_dict.items():
            if isinstance(content, pd.DataFrame):
                # Handle DataFrames
                csv_buffer = BytesIO()
                content.to_csv(csv_buffer, index=False)
                zip_file.writestr(filename, csv_buffer.getvalue())
            else:
                # Handle text content
                zip_file.writestr(filename, content.encode('utf-8'))
    
    return zip_buffer.getvalue()

def get_zip_download_link(zip_content, filename="analysis_results.zip"):
    """Generate a download link for a zip file."""
    b64 = base64.b64encode(zip_content).decode()
    href = (
        f'<a href="data:application/zip;base64,{b64}" '
        f'download="{filename}" class="download-button">'
        f'📥 Download All Results</a>'
    )
    return href

def display_summary_report(df, title_results, meta_results):
    """Display a visually appealing summary report using Streamlit components."""
    
    st.markdown("## 📊 Content Analysis Summary")
    st.markdown(f"*Analysis completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*")
    
    # Normalize column names to lowercase for consistent access
    df.columns = df.columns.str.lower()
    
    # Verify required columns exist
    if 'url' not in df.columns:
        st.error("URL column not found in the dataset.")
        return
        
    # Overall Statistics
    st.markdown("### 📈 Overall Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total URLs", f"{len(df):,}")
    with col2:
        st.metric("Unique URLs", f"{df['url'].nunique():,}")
    with col3:
        st.metric("Page Types", f"{df['pagetype'].nunique():,}")
    
    # Title Analysis
    if title_results and 'title' in df.columns:
        st.markdown("### 📝 Title Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Titles", f"{len(df):,}")
        with col2:
            st.metric("Unique Titles", f"{df['title'].nunique():,}")
        with col3:
            dupes = len(df[df.duplicated(subset=['title'], keep=False)])
            st.metric("Total URLs with Duplicate Title Issues", f"{dupes:,}")
        
        if title_results[4] is not None and not title_results[4].empty:
            st.markdown("#### Most Duplicated Title")
            most_duped = title_results[4].iloc[0]
            title_column = 'title' if 'title' in most_duped else 'Title'  # Handle both cases
            st.info(
                f"**Title:** {most_duped[title_column]}\n\n"
                f"**Times Used:** {most_duped['Duplicate_Count']:,}\n\n"
                f"**Page Types:** {most_duped['Pagetype_List']}"
            )
    
    # Meta Description Analysis
    if meta_results and 'meta_description' in df.columns:
        st.markdown("### 📄 Meta Description Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Meta Descriptions", f"{len(df):,}")
        with col2:
            st.metric("Unique Meta Descriptions", f"{df['meta_description'].nunique():,}")
        with col3:
            dupes = len(df[df.duplicated(subset=['meta_description'], keep=False)])
            st.metric("Total URLs with Duplicate Meta Descriptions Issues", f"{dupes:,}")
        
        if meta_results[4] is not None and not meta_results[4].empty:
            st.markdown("#### Most Duplicated Meta Description")
            most_duped = meta_results[4].iloc[0]
            meta_column = 'meta_description' if 'meta_description' in most_duped else 'Meta Description'
            st.info(
                f"**Meta Description:** {most_duped[meta_column]}\n\n"
                f"**Times Used:** {most_duped['Duplicate_Count']:,}\n\n"
                f"**Page Types:** {most_duped['Pagetype_List']}"
            )
    
    # Page Type Analysis
    if 'pagetype' in df.columns:
        st.markdown("### 📑 Analysis by Page Type")
        
        for pagetype in sorted(df['pagetype'].unique()):
            pagetype_data = df[df['pagetype'] == pagetype]
            with st.expander(f"Page Type: {pagetype} ({len(pagetype_data):,} URLs)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    if title_results and 'title' in df.columns:
                        title_dupes = len(pagetype_data[
                            pagetype_data.duplicated(subset=['title'], keep=False)
                        ])
                        dupe_rate = (title_dupes/len(pagetype_data)*100) if title_dupes > 0 else 0
                        st.metric(
                            "Total URLs with Duplicate Title Issues",
                            f"{title_dupes:,}",
                            f"{dupe_rate:.1f}% of pages"
                        )
                
                with col2:
                    if meta_results and 'meta_description' in df.columns:
                        meta_dupes = len(pagetype_data[
                            pagetype_data.duplicated(subset=['meta_description'], keep=False)
                        ])
                        dupe_rate = (meta_dupes/len(pagetype_data)*100) if meta_dupes > 0 else 0
                        st.metric(
                            "Total URLs with Duplicate Meta Description Issues",
                            f"{meta_dupes:,}",
                            f"{dupe_rate:.1f}% of pages"
                        )

def display_ngram_analysis(title_results, meta_results, analysis_type):
    """Display n-gram analysis results in a structured format."""
    
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

def display_export_options(df, title_results, meta_results, analysis_type):
    """Display and handle export options for analysis results."""
    
    st.subheader("Download Analysis Results")
    
    # Create dictionary of all files to be included in zip
    export_files = {}
    
    if "Titles" in analysis_type and title_results[4] is not None:
        export_files['title_duplicate_rollup.csv'] = title_results[4]
        export_files['title_pagetype_summary.csv'] = title_results[1]
        
        # Add n-gram analyses if they exist
        if title_results[3]:
            for n, df_ngram in title_results[3].items():
                export_files[f'title_{n}gram_analysis.csv'] = df_ngram

    if "Meta Descriptions" in analysis_type and meta_results is not None:
        if meta_results[4] is not None:
            export_files['meta_description_duplicate_rollup.csv'] = meta_results[4]
        export_files['meta_description_pagetype_summary.csv'] = meta_results[1]
        
        # Add n-gram analyses if they exist
        if meta_results[3]:
            for n, df_ngram in meta_results[3].items():
                export_files[f'meta_description_{n}gram_analysis.csv'] = df_ngram
    
    # Generate summary report
    summary_text = generate_summary_report(df, title_results, meta_results)
    export_files['analysis_summary.txt'] = summary_text
    
    # Create and display the zip download button
    zip_content = create_zip_download(export_files)
    st.markdown(
        get_zip_download_link(zip_content),
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # Display visual summary report
    display_summary_report(df, title_results, meta_results)
    
    st.markdown("---")
    st.markdown("### Individual File Downloads")
    
    # Display individual file download links
    for filename, content in export_files.items():
        if isinstance(content, pd.DataFrame):
            st.markdown(
                get_csv_download_link(content, filename),
                unsafe_allow_html=True
            )
        else:
            b64 = base64.b64encode(content.encode()).decode()
            st.markdown(
                f'<a href="data:text/plain;base64,{b64}" '
                f'download="{filename}">Download {filename}</a>',
                unsafe_allow_html=True
            )

def display_content_reference(df, content_type):
    """Display a reference table of all titles or meta descriptions."""
    if content_type == "Title":
        content_col = "title"
    else:
        content_col = "meta_description"

    # Create summary of all content
    content_summary = df.groupby(content_col, dropna=False).agg({
        'url': list,
        'pagetype': lambda x: sorted(set(x))
    }).reset_index()
    
    # Add counts and format
    content_summary['Count'] = content_summary['url'].apply(len)
    content_summary['URLs'] = content_summary['url'].apply(lambda x: '\n'.join(sorted(x)))
    content_summary['Page Types'] = content_summary['pagetype'].apply(lambda x: ', '.join(x))
    
    # Clean up and sort
    content_summary = content_summary[[content_col, 'Count', 'Page Types', 'URLs']]
    content_summary = content_summary.sort_values('Count', ascending=False)
    content_summary[content_col] = content_summary[content_col].fillna("[BLANK]")
    
    st.subheader(f"All {content_type}s Reference")
    st.dataframe(content_summary, use_container_width=True)
    st.markdown(
        get_csv_download_link(
            content_summary,
            f"{content_type.lower()}_reference.csv"
        ),
        unsafe_allow_html=True
    )

def display_duplicate_analysis(title_results, meta_results, analysis_type, df):
    """Display duplicate analysis results with proper empty states and reference tables."""
    if "Titles" in analysis_type:
        st.subheader("Title Duplicate Analysis")
        if title_results and title_results[4] is not None and not title_results[4].empty:
            st.dataframe(title_results[4], use_container_width=True)
            st.markdown(
                get_csv_download_link(
                    title_results[4],
                    "title_duplicate_rollup.csv"
                ),
                unsafe_allow_html=True
            )
        else:
            display_empty_state("Total URLs with Duplicate Titles")
        
        st.subheader("Title Duplication by Page Type")
        if title_results and title_results[1] is not None and not title_results[1].empty:
            st.dataframe(title_results[1], use_container_width=True)
        else:
            display_empty_state("Title Duplication Data")
            
        # Add reference table for all titles
        st.markdown("---")
        display_content_reference(df, "Title")

    if "Meta Descriptions" in analysis_type:
        st.subheader("Meta Description Duplicate Analysis")
        if meta_results and meta_results[4] is not None and not meta_results[4].empty:
            st.dataframe(meta_results[4], use_container_width=True)
            st.markdown(
                get_csv_download_link(
                    meta_results[4],
                    "meta_description_duplicate_rollup.csv"
                ),
                unsafe_allow_html=True
            )
        else:
            display_empty_state("Pages with Duplicate Meta Descriptions")
        
        st.subheader("Meta Description Duplication by Page Type")
        if meta_results and meta_results[1] is not None and not meta_results[1].empty:
            st.dataframe(meta_results[1], use_container_width=True)
        else:
            display_empty_state("Meta Description Duplication Data")
            
        # Add reference table for all meta descriptions
        st.markdown("---")
        display_content_reference(df, "Meta Description")

def display_empty_state(content_type):
    """Display a friendly empty state message with an icon."""
    st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: rgba(0,0,0,0.1); border-radius: 10px; margin: 1rem 0;">
            <div style="font-size: 2rem; margin-bottom: 1rem;">🔍</div>
            <h3 style="margin-bottom: 0.5rem;">No {content_type} Found</h3>
            <p style="color: #666;">No duplicate {content_type.lower()} were detected in your content.</p>
        </div>
    """, unsafe_allow_html=True)

def load_file_with_special_header(uploaded_file, delimiter):
    """
    Load a CSV file that might start with 'sep=' line, with explicit header handling.
    """
    try:
        # Read raw content
        content = uploaded_file.getvalue().decode('utf-8')
        
        # Split into lines and remove empty lines
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        if not lines:
            st.error("File appears to be empty")
            return None
            
        # Define expected headers based on the file preview
        expected_headers = ['Full URL', 'pagetype', 'Title', 'Meta Description']
        
        # Find where the real data starts
        start_idx = None
        for i, line in enumerate(lines):
            if any(header in line for header in expected_headers):
                start_idx = i
                break
                
        if start_idx is None:
            # If we can't find expected headers, try to use the line after 'sep='
            if lines[0].startswith('sep='):
                start_idx = 1
            else:
                start_idx = 0
        
        # Get the actual header line and remaining data
        header_line = lines[start_idx]
        data_lines = lines[start_idx + 1:]
        
        # Create clean CSV content
        clean_csv = header_line + '\n' + '\n'.join(data_lines)
        
        # Read CSV with pandas
        df = pd.read_csv(
            io.StringIO(clean_csv),
            encoding='utf-8',
            on_bad_lines='skip'  # Skip problematic lines
        )
        
        # Clean up column names
        df.columns = [col.strip() for col in df.columns]
        
        # Add debug information
        if st.session_state.get('debug_mode', False):
            st.write("Debug Info:")
            st.write(f"Found headers: {list(df.columns)}")
            st.write(f"Number of rows: {len(df)}")
            with st.expander("Preview clean data"):
                st.write(df.head())
        
        return df
        
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        st.write("Debug information:")
        st.write("File content preview (first few lines):")
        try:
            preview = '\n'.join(lines[:5]) if 'lines' in locals() else 'No preview available'
            st.code(preview)
        except:
            st.write("Could not generate preview")
        st.write("Full error traceback:")
        st.code(traceback.format_exc())
        return None

def inspect_csv_content(uploaded_file):
    """
    Inspect the content of a CSV file to help debug issues.
    """
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        lines = content.splitlines()
        
        st.write("CSV File Inspection:")
        st.write("---")
        
        st.write("First 5 lines of raw content:")
        for i, line in enumerate(lines[:5]):
            st.code(f"Line {i + 1}: {line}")
            
        # Try to detect delimiter
        first_line = lines[0] if lines else ''
        delimiters = [',', '\t', ';', '|']
        detected_delims = [d for d in delimiters if d in first_line]
        
        st.write("\nDelimiter Analysis:")
        for d in detected_delims:
            count = first_line.count(d)
            st.write(f"Found {count} instances of '{d}'")
            
        return True
    except Exception as e:
        st.error(f"Error inspecting CSV: {str(e)}")
        return False

def main():
    header_container = st.container()
    with header_container:
        col1, col2 = st.columns([1, 11])
        with col1:
            if st.button("🔄 Reset", help="Clear all data and start over"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        with col2:
            st.title("SEO Content SuperScope")
            st.write("""
            Analyze SEO content elements (titles, meta descriptions) to identify patterns, duplicates, and n-gram frequencies from CSV exports (Screaming Frog, Sitebulb).
            
            Created by [Jimmy Lange](https://jamesrobertlange.com).
            
            Watch below for a quick overview of the tool's features and capabilities:
            """)
            
            vid_col1, vid_col2, vid_col3 = st.columns([1,2,1])
            with vid_col2:
                st.video('https://www.youtube.com/watch?v=xlUXNWry-Ig')

    # File upload
    uploaded_file = st.file_uploader(
        "Upload your CSV/TSV file",
        type=['csv', 'tsv'],
        help="File should contain columns for URL, Title, Meta Description, and Page Type"
    )

    if uploaded_file:
        try:
            # Add debug option in sidebar
            debug_mode = st.sidebar.checkbox("Debug Mode", value=False)
            
            if debug_mode:
                with st.expander("CSV File Inspection Results"):
                    inspect_csv_content(uploaded_file)
            
            # File configuration in sidebar
            st.sidebar.header("File Settings")
            delimiter = st.sidebar.selectbox(
                "File delimiter",
                options=[',', '\t', ';', '|'],
                index=0,
                format_func=lambda x: 'Tab' if x == '\t' else x
            )

            # Reset file pointer before reading
            uploaded_file.seek(0)
            
            # Read the file
            df = load_file_with_special_header(uploaded_file, delimiter)
            
            if df is not None:
                if debug_mode:
                    st.write("Loaded DataFrame Info:")
                    st.write(f"Shape: {df.shape}")
                    st.write("Columns:", list(df.columns))
                    with st.expander("Preview Data"):
                        st.dataframe(df.head())

                if not st.session_state.mapping_complete:
                    mapped_df = display_column_mapper(df)
                    if mapped_df is not None:
                        st.session_state.mapped_df = mapped_df
                        st.session_state.mapping_complete = True
                        st.success("Column mapping confirmed! You can now proceed with the analysis.")
                        st.session_state.analysis_complete = False
                        st.session_state.results = {}
                
                # Only proceed with analysis if mapping is complete
                if st.session_state.mapping_complete and st.session_state.mapped_df is not None:
                    df = st.session_state.mapped_df  # Use the mapped DataFrame

                    # Display basic file info
                    st.subheader("File Overview")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total URLs", f"{len(df):,}")
                    with col2:
                        st.metric("Unique URLs", f"{df['url'].nunique():,}")
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

                    # Define button styles
                    st.markdown("""
                        <style>
                        div.stButton > button:first-child {
                            height: 3em;
                            width: 100%;
                            font-size: 20px;
                            font-weight: bold;
                            border: none;
                            border-radius: 4px;
                            margin: 1em 0;
                        }
                        
                        div.stButton.confirmation-button > button:first-child {
                            background-color: #FF4B4B;
                            color: white;
                        }
                        div.stButton.confirmation-button > button:hover {
                            background-color: #FF6B6B;
                        }
                        
                        div.stButton.analysis-button > button:first-child {
                            background-color: #0096FF;
                            color: white;
                        }
                        div.stButton.analysis-button > button:hover {
                            background-color: #0078CC;
                        }
                        </style>
                    """, unsafe_allow_html=True)

                    # Create a centered container for the analyze button
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.markdown('<div class="analysis-button">', unsafe_allow_html=True)
                        if st.button("🔍 Run Analysis"):
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
                        st.markdown('</div>', unsafe_allow_html=True)

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
                        
                        if tab_options:  # Only create tabs if there are options
                            tabs = st.tabs(tab_options)
                            tab_index = 0

                            # Title Analysis Tab
                            if "Titles" in analysis_type:
                                with tabs[tab_index]:
                                    display_duplicate_analysis(title_results, None, ["Titles"], df)
                                tab_index += 1

                            # Meta Description Analysis Tab
                            if "Meta Descriptions" in analysis_type:
                                with tabs[tab_index]:
                                    display_duplicate_analysis(None, meta_results, ["Meta Descriptions"], df)
                                tab_index += 1

                            # N-gram Analysis Tab
                            if include_ngrams and len(ngram_sizes) > 0:
                                with tabs[tab_index]:
                                    display_ngram_analysis(title_results, meta_results, analysis_type)
                                tab_index += 1

                            # Export Results Tab
                            with tabs[tab_index]:
                                display_export_options(df, title_results, meta_results, analysis_type)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            if debug_mode:
                with st.expander("Show Debug Information"):
                    st.code(traceback.format_exc())
    
    else:
        st.info("Please upload a CSV or TSV file to begin.")

if __name__ == "__main__":
    main()