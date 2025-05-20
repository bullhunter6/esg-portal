"""
Authentication blueprint for user management
"""
from flask import Blueprint

bp = Blueprint('auth', __name__)

from esg_portal.auth import routes 