from flask import Blueprint, render_template, Flask

# Define the blueprint
views = Blueprint('views', __name__, static_folder='static')


@views.route('/changepic')
def changepic():
    return render_template('changepic.html')

