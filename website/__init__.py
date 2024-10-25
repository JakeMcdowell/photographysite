from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from django.shortcuts import render

db = SQLAlchemy()
DB_NAME = "datacase.db"

# Global variable to store the filename of the "Pic of the Day"
pic_of_the_day = "default.jpg"

def create_app(): 
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'SHHHHH'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    UPLOAD_FOLDER = 'website/static/images/'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB

    from .views import views

    @app.route('/', methods=['GET', 'POST'])
    def index():
        # Check if a gallery button was clicked (POST request)
        selected_gallery = None
        if request.method == 'POST':
            selected_gallery = request.form.get('gallery')

        # Default to 'sen-por' if no selection
        if selected_gallery is None:
            selected_gallery = 'sen-por'

        return render_template('index.html', filename=pic_of_the_day, selected_gallery=selected_gallery)

    @app.route('/change-pic')
    def change_pic():
        # get file name lope
        return render_template('changepic.html')

    @app.route('/update-pic', methods=['POST'])
    def update_pic():

        global pic_of_the_day  # Declare pic_of_the_day as global
        
        if 'newPic' not in request.files:
            return 'No file part'
        
        file = request.files['newPic']
        if file.filename == '':
            return 'No selected file'

        if file:
            # Delete the previous image if it exists
            if pic_of_the_day:
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], pic_of_the_day)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            # Save the new image
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Update the global variable to the new filename
            pic_of_the_day = filename

             # Path to the picture directory
            picture_folder = os.path.join(app.static_folder, 'picture')
            
            # Get all image filenames in the picture directory
            pictures = [f'picture/{file}' for file in os.listdir(picture_folder) if file.endswith(('jpg', 'jpeg', 'png', 'gif'))]

            
            return redirect(url_for('index', pictures=pictures))

    def carousel_view(request):
    # Default context with no carousel selected
        context = {
            'selected_carousel': None,
        }

    # Check if the form was submitted with a carousel selection
        if request.method == "POST":
            # Get the selected carousel from the form data
            selected_carousel = request.POST.get('carousel')
            
            # Pass the selected carousel to the context to render the correct one
            context['selected_carousel'] = selected_carousel

        # Render the template with the selected carousel
        return render(request, 'carousel_template.html', context)   

    app.register_blueprint(views, url_prefix='/')
    return app
