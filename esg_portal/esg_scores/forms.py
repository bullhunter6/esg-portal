"""
Form classes for ESG Scores module
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class SearchForm(FlaskForm):
    """Form for searching ESG scores by company name"""
    company_name = StringField('Company Name', 
                              validators=[DataRequired(), Length(min=2, max=100)],
                              render_kw={"placeholder": "Enter company name (e.g., Apple)"})
    submit = SubmitField('Search ESG Scores')

class UploadForm(FlaskForm):
    """Form for uploading Excel files to update with ESG scores"""
    file = FileField('Excel File', 
                    validators=[
                        FileRequired(), 
                        FileAllowed(['xlsx', 'xls'], 'Excel files only!')
                    ],
                    render_kw={"accept": ".xlsx,.xls"})
    company_search = StringField('Company Name Column', 
                               validators=[Optional(), Length(max=50)],
                               render_kw={"placeholder": "Column name containing company names (optional)"})
    submit = SubmitField('Upload and Process File') 