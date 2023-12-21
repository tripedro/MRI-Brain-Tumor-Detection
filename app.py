from flask import Flask, request, jsonify, render_template, url_for
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow import keras
import os
import random
import sys

import logging
import hashlib
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# intialize app
app = Flask(__name__, static_folder='mri-images')

# Log Python and TensorFlow versions
logger.info(f"Python version: {sys.version}")
logger.info(f"TensorFlow version: {tf.__version__}")

script_dir = os.path.dirname(__file__)
model_dir = os.path.join(script_dir, 'models')
model_path = os.path.join(model_dir, 'brain_tumor_cnn_classifier.keras')

# Log model path
logger.info(f"Model path: {model_path}")

# check if the model file exists
if os.path.exists(model_path):
    logger.info("Model file found.")
else:
    logger.error("Model file not found.")

# check model file
def get_file_info(file_path):
    file_info = {
        'exists': os.path.exists(file_path),
        'size': None,
        'md5_checksum': None
    }

    if file_info['exists']:
        file_info['size'] = os.path.getsize(file_path)

        # Calculate MD5 checksum
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_info['md5_checksum'] = hash_md5.hexdigest()

    return file_info

model_info = get_file_info(model_path)
logger.info(f"Model Exists: {model_info['exists']}")
logger.info(f"Model File Size: {model_info['size']} bytes")
logger.info(f"Model MD5 Checksum: {model_info['md5_checksum']}")

try:
    CNN = tf.keras.models.load_model(model_path, compile=False)
    logger.info("Model loaded successfully.")

    logger.info(f"Model Type: {type(CNN)}")
    logger.info("Model Summary:")
    model_summary = []
    CNN.summary(print_fn=lambda x: model_summary.append(x))
    model_summary_str = "\n".join(model_summary)
    logger.info(model_summary_str)

    # for layer in CNN.layers:
    #     weights = layer.get_weights()
    #     logger.info(f"Layer: {layer.name}, Weights: {weights}")

    CNN.compile(optimizer=tf.keras.optimizers.Adamax(learning_rate=0.001), 
                loss='categorical_crossentropy', 
                metrics=['accuracy'])
except Exception as e:
    logger.error(f"Error loading model: {e}")

    
# function for retrieving prediction from model given an image path
def get_model_prediction(image_path):
    try:
        # load and preprocess the image
        img = Image.open(image_path).resize((224, 224))
        # convert grayscale images to RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.expand_dims(np.array(img), axis=0)
        
        # predict using the CNN model
        prediction = CNN.predict(img_array)
        
        # interpret the prediction
        predicted_index = np.argmax(prediction[0])
        class_labels = ['glioma', 'meningioma', 'no tumor', 'pituitary']
        predicted_class = class_labels[predicted_index]
        logger.info(f"Prediction for image {image_path}: {predicted_class}")
        return predicted_class
    except Exception as e:
        logger.error(f"Error in get_model_prediction: {e}")
        return None

# load html template
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-random-image', methods=['GET'])
def get_random_image():
    try:  
         # select a random directory and then a random image within the image directory
        class_dirs = ['glioma', 'meningioma', 'notumor', 'pituitary']
        selected_class = random.choice(class_dirs)
        image_dir = os.path.join('mri-images', selected_class)
        image_name = random.choice(os.listdir(image_dir))
        image_path = os.path.join(image_dir, image_name)
        predicted_label = get_model_prediction(image_path)
        web_accessible_image_path = url_for('static', filename=f'{selected_class}/{image_name}')
        logger.info(f"Random image selected: {image_path}")
        return jsonify({
            'image_path': web_accessible_image_path,
            'actual_label': selected_class,
            'predicted_label': predicted_label
        })
    except Exception as e:
        logger.error(f"Error in get-random-image route: {e}")
        return jsonify({'error': 'An error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True)
