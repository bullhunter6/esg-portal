"""
API blueprint for RESTful endpoints
"""
from flask import Blueprint

bp = Blueprint('api', __name__)

from esg_portal.api import routes 