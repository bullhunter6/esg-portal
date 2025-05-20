"""
Core blueprint for main application functionality
"""
from flask import Blueprint

bp = Blueprint('core', __name__)

from esg_portal.core import routes 