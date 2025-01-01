from flask import Blueprint, render_template

# Define the blueprint
views = Blueprint('views', __name__, static_folder='static')


@views.route('/')
def changepictures():
    return render_template('')

