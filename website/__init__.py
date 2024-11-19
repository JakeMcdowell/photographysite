from flask import Flask, render_template, request, redirect, url_for, current_app
import os
from werkzeug.utils import secure_filename
from django.shortcuts import render

upload_new_picture = "default.jpg"

def create_app():
    app = Flask(__name__)
      
    app.config['POFD_FOLDER'] = 'website/static/images/'
    app.config['CAROUSEL_FOLDER'] = 'website/static/picture/'
    
    
    from .views import views 

    @app.route('/', methods=['GET', 'POST'])
    def index():
        categories = {
            "sen-por": "senior-pic",
            "headshots": "headshot-pic",
            "baby-pic": "infant-pic",
            "landscapes": "landscape-pic",
            "pets": "pets-pic",
            "special-events": "sp-event-pic",
            "sports": "sports-pic"
        }

        # Handle gallery selection via POST
        selected_category = request.form.get('gallery', 'sen-por')  # Default to 'sen-por'
        carousel_path = app.config['CAROUSEL_FOLDER']
        selected_folder = categories.get(selected_category, "senior-pic")
        gallery_path = os.path.join(carousel_path, selected_folder)

        # Fetch image files for the selected category
        image_files = []
        if os.path.exists(gallery_path):
            image_files = [
                img for img in os.listdir(gallery_path)
                if img.lower().endswith(('jpg', 'jpeg', 'png', 'gif'))
            ]

        return render_template(
            'index.html',
            filename=upload_new_picture,
            selected_gallery=selected_category,
            image_files=image_files,
            categories=categories
        )



    
    @app.route('/changepic')
    def change_pic():
        base_path = os.path.join(app.static_folder, 'picture')
        categories = ["senior-pic", "headshot-pic", "infant-pic", "landscape-pic", "pets-pic", "sp-event-pic", "sports-pic"]
        
        images_by_category = {}
        for category in categories:
            category_path = os.path.join(base_path, category)
            images_by_category[category] = [f'picture/{category}/{img}' for img in os.listdir(category_path) if img.endswith(('jpg', 'jpeg', 'png', 'gif'))]
        
        return render_template('changepic.html', images_by_category=images_by_category)

    @app.route('/update-potd', methods=['POST'])
    def update_potd():

        global upload_new_picture  
        
        if 'newPic' not in request.files:
            return 'No file part'
        
        file = request.files['newPic']
        if file.filename == '':
            return 'No selected file'

        if file:
            # Delete the previous image if it exists
            if upload_new_picture:
                old_filepath = os.path.join(app.config['POFD_FOLDER'], upload_new_picture)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            # Save the new image
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['POFD_FOLDER'], filename)
            file.save(filepath)
            
            # Update the global variable to the new filename
            upload_new_picture = filename

             # Path to the picture directory
            picture_folder = os.path.join(app.static_folder, 'picture')
            
            # Get all image filenames in the picture directory
            pictures = [f'picture/{file}' for file in os.listdir(picture_folder) if file.endswith(('jpg', 'jpeg', 'png', 'gif'))]

            
            return redirect(url_for('index', pictures=pictures))

    @app.route('/update-carousel', methods=['POST'])
    def update_pic():
        global upload_new_picture  # Declare upload_new_picture as global

        category = request.form.get('category')
        file = request.files['newCarousel']

        if not category or not file or file.filename == '':
            return 'No file or category selected', 400


        if file:
            category_folder = os.path.join(app.static_folder, 'picture', category)
            if not os.path.exists(category_folder):
                os.makedirs(category_folder)
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(category_folder, filename)
            file.save(filepath)
            
            upload_new_picture = filename
            return redirect(url_for('change_pic'))

    @app.route('/delete-pic', methods=['POST'])
    def delete_pic():
        newCarousel = request.form.get('newCarousel')
        if newCarousel:
            full_path = os.path.join(app.static_folder, newCarousel)
            if os.path.exists(full_path):
                os.remove(full_path)
                return redirect(url_for('change_pic'))
        return 'Image not found', 404
    
    app.register_blueprint(views, url_prefix='/')
    return app
