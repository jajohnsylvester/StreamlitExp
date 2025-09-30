import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json

# Page configuration
st.set_page_config(page_title="Personal Expense Tracker", page_icon="💰", layout="wide")

# Google Sheets Setup
@st.cache_resource
def get_google_sheet():
    """Connect to Google Sheets"""
    try:
        # Get credentials from Streamlit secrets
        credentials_dict = st.secrets["gcp_service_account"]
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        
        # Open the spreadsheet (you can use spreadsheet name or key)
        sheet_name = st.secrets.get("sheet_name", "Personal Expense Tracker")
        
        try:
            spreadsheet = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            # Create new spreadsheet if it doesn't exist
            spreadsheet = client.create(sheet_name)
            spreadsheet.share('', perm_type='anyone', role='writer')
        
        return spreadsheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None

def get_expenses_worksheet(spreadsheet):
    """Get or create Expenses worksheet"""
    try:
        worksheet = spreadsheet.worksheet("Expenses")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Expenses", rows=1000, cols=10)
        worksheet.update('A1:D1', [['Date', 'Amount', 'Category', 'Description']])
    return worksheet

def get_categories_worksheet(spreadsheet):
    """Get or create Categories worksheet"""
    try:
        worksheet = spreadsheet.worksheet("Categories")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Categories", rows=100, cols=1)
        worksheet.update('A1', [['Category']])
        # Add default categories
        default_categories = [
            ["Food & Dining"],
            ["Transportation"],
            ["Shopping"],
            ["Entertainment"],
            ["Bills & Utilities"],
            ["Healthcare"],
            ["Education"],
            ["Travel"],
            ["Groceries"],
            ["Other"]
        ]
        worksheet.append_rows(default_categories)
    return worksheet

def load_categories(worksheet):
    """Load categories from Google Sheets"""
    try:
        data = worksheet.get_all_records()
        if data:
            return [row['Category'] for row in data]
        return []
    except Exception as e:
        st.error(f"Error loading categories: {str(e)}")
        return []

def add_category(worksheet, category):
    """Add a new category"""
    try:
        worksheet.append_row([category])
        return True
    except Exception as e:
        st.error(f"Error adding category: {str(e)}")
        return False

def delete_category(worksheet, category):
    """Delete a category"""
    try:
        cell = worksheet.find(category)
        if cell:
            worksheet.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting category: {str(e)}")
        return False

def load_expenses(worksheet):
    """Load expenses from Google Sheets"""
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            df['Amount'] = pd.to_numeric(df['Amount'])
            # Add row numbers for editing/deleting
            df['RowNum'] = range(2, len(df) + 2)  # +2 because row 1 is header and sheets are 1-indexed
            return df
        return pd.DataFrame(columns=['Date', 'Amount', 'Category', 'Description', 'RowNum'])
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(columns=['Date', 'Amount', 'Category', 'Description', 'RowNum'])

def add_expense(worksheet, date, amount, category, description):
    """Add a new expense to Google Sheets"""
    try:
        row = [date.strftime('%Y-%m-%d'), float(amount), category, description]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error adding expense: {str(e)}")
        return False

def update_expense(worksheet, row_num, date, amount, category, description):
    """Update an existing expense"""
    try:
        worksheet.update(f'A{row_num}:D{row_num}', [[date.strftime('%Y-%m-%d'), float(amount), category, description]])
        return True
    except Exception as e:
        st.error(f"Error updating expense: {str(e)}")
        return False

def delete_expense(worksheet, row_num):
    """Delete an expense"""
    try:
        worksheet.delete_rows(row_num)
        return True
    except Exception as e:
        st.error(f"Error deleting expense: {str(e)}")
        return False

def clear_all_expenses(worksheet):
    """Clear all expenses from Google Sheets"""
    try:
        worksheet.clear()
        worksheet.update('A1:D1', [['Date', 'Amount', 'Category', 'Description']])
        return True
    except Exception as e:
        st.error(f"Error clearing data: {str(e)}")
        return False

# Title
st.title("💰 Personal Expense Tracker")
st.markdown("*Data stored in Google Sheets*")
st.markdown("---")

# Setup instructions in expander
with st.expander("📋 Setup Instructions"):
    st.markdown("""
    ### Google Sheets API Setup:
    
    1. **Create a Google Cloud Project:**
       - Go to [Google Cloud Console](https://console.cloud.google.com/)
       - Create a new project
    
    2. **Enable Google Sheets API:**
       - In your project, enable "Google Sheets API" and "Google Drive API"
    
    3. **Create Service Account:**
       - Go to "IAM & Admin" > "Service Accounts"
       - Create a service account
       - Create a JSON key and download it
    
    4. **Add Credentials to Streamlit:**
       - Create a `.streamlit/secrets.toml` file in your project directory
       - Add your credentials:
       
    ```toml
    sheet_name = "Personal Expense Tracker"
    
    [gcp_service_account]
    type = "service_account"
    project_id = "your-project-id"
    private_key_id = "your-private-key-id"
    private_key = "-----BEGIN PRIVATE KEY-----\\nYour-Private-Key\\n-----END PRIVATE KEY-----\\n"
    client_email = "your-service-account@your-project.iam.gserviceaccount.com"
    client_id = "your-client-id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "your-cert-url"
    ```
    
    5. **Install Required Packages:**
    ```bash
    pip install streamlit pandas plotly gspread google-auth
    ```
    """)

# Try to connect to Google Sheets
spreadsheet = get_google_sheet()

if spreadsheet is None:
    st.error("⚠️ Unable to connect to Google Sheets. Please check your credentials.")
    st.info("👆 Click 'Setup Instructions' above to configure Google Sheets API.")
    st.stop()

expenses_worksheet = get_expenses_worksheet(spreadsheet)
categories_worksheet = get_categories_worksheet(spreadsheet)

# Load categories
categories = load_categories(categories_worksheet)

# Sidebar for adding expenses and managing categories
with st.sidebar:
    st.header("Add New Expense")
    
    with st.form("expense_form"):
        amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
        category = st.selectbox("Category", categories if categories else ["Other"])
        description = st.text_input("Description")
        date = st.date_input("Date", value=datetime.now())
        
        submitted = st.form_submit_button("Add Expense", use_container_width=True)
        
        if submitted:
            if add_expense(expenses_worksheet, date, amount, category, description):
                st.success("✅ Expense added successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to add expense.")
    
    st.markdown("---")
    
    # Manage Categories
    st.header("Manage Categories")
    
    with st.expander("➕ Add New Category"):
        with st.form("add_category_form"):
            new_category = st.text_input("Category Name")
            add_cat_btn = st.form_submit_button("Add Category", use_container_width=True)
            
            if add_cat_btn and new_category:
                if new_category in categories:
                    st.warning("⚠️ Category already exists!")
                elif add_category(categories_worksheet, new_category):
                    st.success(f"✅ Added '{new_category}'!")
                    st.rerun()
    
    with st.expander("🗑️ Delete Category"):
        if categories:
            with st.form("delete_category_form"):
                cat_to_delete = st.selectbox("Select Category to Delete", categories)
                del_cat_btn = st.form_submit_button("Delete Category", use_container_width=True, type="secondary")
                
                if del_cat_btn and cat_to_delete:
                    if delete_category(categories_worksheet, cat_to_delete):
                        st.success(f"✅ Deleted '{cat_to_delete}'!")
                        st.rerun()
        else:
            st.info("No categories to delete")
    
    with st.expander("📋 View All Categories"):
        if categories:
            for i, cat in enumerate(categories, 1):
                st.write(f"{i}. {cat}")
        else:
            st.info("No categories found")

# Load expenses
df = load_expenses(expenses_worksheet)

# Main content
if len(df) == 0:
    st.info("👈 Start by adding your first expense using the sidebar!")
else:
    # Rename columns for consistency
    df = df.rename(columns={'Date': 'date', 'Amount': 'amount', 'Category': 'category', 'Description': 'description', 'RowNum': 'row_num'})
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Expenses", f"${df['amount'].sum():,.2f}")
    
    with col2:
        st.metric("Number of Transactions", len(df))
    
    with col3:
        st.metric("Average Transaction", f"${df['amount'].mean():,.2f}")
    
    with col4:
        most_expensive = df.loc[df['amount'].idxmax()]
        st.metric("Highest Expense", f"${most_expensive['amount']:,.2f}")
    
    st.markdown("---")
    
    # Filters
    st.subheader("📊 Expense Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_range = st.date_input(
            "Date Range",
            value=(df['date'].min().date(), df['date'].max().date()),
            key="date_range"
        )
    
    with col2:
        available_categories = df['category'].unique().tolist()
        selected_categories = st.multiselect(
            "Filter by Category",
            options=available_categories,
            default=available_categories
        )
    
    with col3:
        min_amount = st.number_input("Min Amount ($)", min_value=0.0, value=0.0)
    
    # Apply filters
    filtered_df = df[
        (df['date'].dt.date >= date_range[0]) &
        (df['date'].dt.date <= date_range[1]) &
        (df['category'].isin(selected_categories)) &
        (df['amount'] >= min_amount)
    ].copy()
    
    if len(filtered_df) == 0:
        st.warning("No expenses match your filters.")
    else:
        # Visualizations
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Charts", "📋 Data Table", "✏️ Edit/Delete", "💡 Insights"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Spending by category
                category_spending = filtered_df.groupby('category')['amount'].sum().sort_values(ascending=False)
                fig_pie = px.pie(
                    values=category_spending.values,
                    names=category_spending.index,
                    title="Spending by Category",
                    hole=0.4
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Category bar chart
                fig_bar = px.bar(
                    category_spending,
                    x=category_spending.values,
                    y=category_spending.index,
                    orientation='h',
                    title="Total Spending by Category",
                    labels={'x': 'Amount ($)', 'y': 'Category'}
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Daily spending trend
            daily_spending = filtered_df.groupby(filtered_df['date'].dt.date)['amount'].sum().reset_index()
            daily_spending.columns = ['Date', 'Amount']
            
            fig_line = px.line(
                daily_spending,
                x='Date',
                y='Amount',
                title="Daily Spending Trend",
                markers=True
            )
            fig_line.update_layout(xaxis_title="Date", yaxis_title="Amount ($)")
            st.plotly_chart(fig_line, use_container_width=True)
        
        with tab2:
            # Data table
            st.subheader(f"All Transactions ({len(filtered_df)} records)")
            
            # Sort and display
            display_df = filtered_df.sort_values('date', ascending=False).copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(
                display_df[['date', 'amount', 'category', 'description']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "date": "Date",
                    "amount": "Amount",
                    "category": "Category",
                    "description": "Description"
                }
            )
            
            # Export option
            csv = filtered_df[['date', 'amount', 'category', 'description']].to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Refresh button
            if st.button("🔄 Refresh Data from Google Sheets"):
                st.cache_resource.clear()
                st.rerun()
        
        with tab3:
            # Edit/Delete Transactions
            st.subheader("✏️ Edit or Delete Transactions")
            
            # Sort by date for better selection
            sorted_df = df.sort_values('date', ascending=False)
            
            # Create display options
            options = []
            for idx, row in sorted_df.iterrows():
                display_text = f"{row['date'].strftime('%Y-%m-%d')} | ${row['amount']:.2f} | {row['category']} | {row['description']}"
                options.append((display_text, idx))
            
            selected_display = st.selectbox(
                "Select Transaction",
                options=[opt[0] for opt in options],
                key="transaction_selector"
            )
            
            if selected_display:
                # Find the selected transaction
                selected_idx = next(opt[1] for opt in options if opt[0] == selected_display)
                selected_row = sorted_df.loc[selected_idx]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📝 Edit Transaction")
                    with st.form("edit_form"):
                        edit_date = st.date_input("Date", value=selected_row['date'])
                        edit_amount = st.number_input("Amount ($)", value=float(selected_row['amount']), min_value=0.01, step=0.01, format="%.2f")
                        edit_category = st.selectbox("Category", categories, index=categories.index(selected_row['category']) if selected_row['category'] in categories else 0)
                        edit_description = st.text_input("Description", value=selected_row['description'])
                        
                        edit_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                        
                        if edit_btn:
                            if update_expense(expenses_worksheet, selected_row['row_num'], edit_date, edit_amount, edit_category, edit_description):
                                st.success("✅ Transaction updated!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to update transaction.")
                
                with col2:
                    st.markdown("### 🗑️ Delete Transaction")
                    st.info(f"**Date:** {selected_row['date'].strftime('%Y-%m-%d')}\n\n**Amount:** ${selected_row['amount']:.2f}\n\n**Category:** {selected_row['category']}\n\n**Description:** {selected_row['description']}")
                    
                    if st.button("🗑️ Delete This Transaction", type="secondary", use_container_width=True):
                        if st.session_state.get('confirm_delete') == selected_idx:
                            if delete_expense(expenses_worksheet, selected_row['row_num']):
                                st.success("✅ Transaction deleted!")
                                st.session_state.confirm_delete = None
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete transaction.")
                        else:
                            st.session_state.confirm_delete = selected_idx
                            st.warning("⚠️ Click 'Delete This Transaction' again to confirm.")
        
        with tab4:
            # Insights
            st.subheader("💡 Spending Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Top Categories")
                top_categories = filtered_df.groupby('category')['amount'].sum().sort_values(ascending=False).head(3)
                for i, (cat, amt) in enumerate(top_categories.items(), 1):
                    percentage = (amt / filtered_df['amount'].sum()) * 100
                    st.write(f"{i}. **{cat}**: ${amt:,.2f} ({percentage:.1f}%)")
                
                st.markdown("### Spending Frequency")
                freq = filtered_df['category'].value_counts().head(3)
                for i, (cat, count) in enumerate(freq.items(), 1):
                    st.write(f"{i}. **{cat}**: {count} transactions")
            
            with col2:
                st.markdown("### Recent Expenses")
                recent = filtered_df.sort_values('date', ascending=False).head(5)
                for _, row in recent.iterrows():
                    st.write(f"**${row['amount']:,.2f}** - {row['category']}")
                    st.caption(f"{row['description']} ({row['date'].strftime('%Y-%m-%d')})")
                
                st.markdown("### Statistics")
                st.write(f"**Daily Average**: ${filtered_df['amount'].sum() / max(len(filtered_df['date'].unique()), 1):,.2f}")
                st.write(f"**Median Transaction**: ${filtered_df['amount'].median():,.2f}")
    
    # Clear data option
    st.markdown("---")
    if st.button("🗑️ Clear All Data", type="secondary"):
        if st.session_state.get('confirm_clear', False):
            if clear_all_expenses(expenses_worksheet):
                st.success("✅ All expenses cleared!")
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.error("❌ Failed to clear expenses.")
        else:
            st.session_state.confirm_clear = True
            st.warning("⚠️ Click again to confirm deletion of all expenses from Google Sheets.")
    
    if st.session_state.get('confirm_clear', False):
        if st.button("Cancel"):
            st.session_state.confirm_clear = False
            st.rerun()
