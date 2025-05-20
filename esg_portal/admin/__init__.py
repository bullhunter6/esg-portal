"""
Admin module for the ESG News Portal
"""
from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/admin')

from esg_portal.admin import routes 