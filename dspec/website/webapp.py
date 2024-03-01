from flask import Flask, render_template, request, send_from_directory
import os
app = Flask(__name__)
from flask import jsonify

EXTERNAL_IMAGES_FOLDER = '/common/lwa/spec/'
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-avail-day')
def get_avail_day():
    # from list of file in daily folder, get the dates
    # return the dates
    available_dates = []
    for f in os.listdir(EXTERNAL_IMAGES_FOLDER + 'daily/'):
        fname = (f.split('.')[0])
        available_dates.append(f'{fname[0:4]}-{fname[4:6]}-{fname[6:8]}')
    print(available_dates)
    return jsonify(available_dates)



@app.route('/get-image', methods=['POST'])
def get_image():
    date = request.form['date']
    # Function to find multiple image paths based on the date
    image_paths = find_images_for_date(date)

    print(image_paths)
    # Construct URLs for the images
    image_urls = [f'/lwa/extm/{path}' for path in image_paths]
    return jsonify({'image_urls': image_urls})


@app.route('/extm/<path:filename>')
def get_external_image(filename):
    print(filename)
    return send_from_directory(EXTERNAL_IMAGES_FOLDER, filename)

from glob import glob

def find_images_for_date(date):
    # Split the date into year, month, and day
    yyyy, mm, dd = date.split('-')

    # Construct the file path
    daily_fname = f'{EXTERNAL_IMAGES_FOLDER}daily/{yyyy}{mm}{dd}.png'

    print(daily_fname)
    # Check if the file exists

    image_paths = []

    if os.path.exists(daily_fname):
        # If the file exists, return the path relative to EXTERNAL_IMAGES_FOLDER
        image_paths.append( 'daily/' + f'{yyyy}{mm}{dd}.png')
        hourly_dir = f'{EXTERNAL_IMAGES_FOLDER}hourly/{yyyy}{mm}/'
        hourly_files = glob(hourly_dir + f'/{dd}_*.png')
        image_paths.extend( [ f'hourly/{yyyy}{mm}/' + os.path.basename(f) for f in hourly_files])
        print(image_paths)
        return image_paths

    else:
        # If the file doesn't exist, you can return a default image or an error
        return []  # Replace with your default image path

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="127.0.0.1", port=5001)
