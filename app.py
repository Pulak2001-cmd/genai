from flask import *
from flask_restful import Resource, Api
from flask_cors import CORS
import openai, imageio, firebase_admin, os
from gtts import gTTS
from PIL import Image
from mutagen.mp3 import MP3
from moviepy import editor
from firebase_admin import credentials, firestore, storage
from datetime import datetime


app = Flask(__name__, static_folder='images')
app.secret_key = 'cfhveyftgyefbf'
cors = CORS(app)
api = Api(app)
api_key = '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'
cred = credentials.Certificate("genai-18270-984e78290b12.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'genai-18270.appspot.com'
})
db = firestore.client()
bucket = storage.bucket()


def generate_paragraph_gpt(topic, num_lines=25):
    openai.api_key = api_key
    prompt = f"Generate a paragraph on the topic: {topic}\n"

    Response = openai.Completion.create(
        engine='text-davinci-002',
        prompt=prompt,
        max_tokens=500
    )

    paragraph = Response.choices[0].text.strip()
    print(paragraph)
    return paragraph

def generate_audio(text, output_file):
    tts = gTTS(text=text, lang='en')
    tts.save(output_file)

def create_vid(audio_path, video_name):
    image = Image.open('images/background.jfif').resize((400, 400), Image.AFFINE)
    audio = MP3(audio_path)
    duration = audio.info.length
    print(duration)
    imageio.mimsave('images.gif', [image], duration=duration)

    video = editor.VideoFileClip("images.gif")
    audio = editor.AudioFileClip(audio_path)
    final_video = video.set_audio(audio)
    final_video.write_videofile(fps=60, codec='libx264', filename=video_name)

def errorMessage(msg):
    return jsonify({'error': msg, 'status': False})


class create_text(Resource):
    def post(self):
        data = request.get_json()
        if "prompt" in data:
            prompt = data['prompt']
        else:
            return errorMessage("Prompt is required")
        paragraph = generate_paragraph_gpt(prompt, num_lines=20)
        return jsonify({"msg": paragraph})

class create_video(Resource):
    def post(self):
        data = request.get_json()
        if "prompt" in data:
            prompt = data['prompt']
        else:
            return errorMessage("Prompt is required")
        paragraph = generate_paragraph_gpt(prompt, num_lines=20)
        generate_audio(paragraph, 'output.mp3')
        tm = f"output{datetime.now().timestamp()}.mp4"
        create_vid('output.mp3', tm)
        blob = bucket.blob(tm)
        blob.upload_from_filename(tm)
        download_url = blob.public_url
        db.collection('videos').add({
            'prompt': prompt,
            'download_url': download_url,
            'filename': tm
        })
        os.remove(tm)
        return jsonify({'msg': 'Video created Successfully'})

api.add_resource(create_video, '/v1/api/create')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    