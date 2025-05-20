"""
ESG Scores module for the ESG Portal
"""
from flask import Blueprint

bp = Blueprint('esg_scores', __name__, url_prefix='/esg-scores')

from esg_portal.esg_scores import routes_simplified as routes