import os
import json
from gtts import gTTS
import pyaudio
import wave
import speech_recognition as sr
from pydub import AudioSegment
from googletrans import Translator

LANGUAGE_OPTIONS = {
    '1': ('hindi', 'hi'),
    '2': ('english', 'en'),
    '3': ('marathi', 'mr'),
    '4': ('tamil', 'ta'),
    '5': ('telugu', 'te'),
    '6': ('kannada', 'kn')
}

def convert_to_pcm(input_file, output_file):
    audio = AudioSegment.from_wav(input_file)
    if audio.sample_width == 2 and audio.frame_rate == 44100:
        audio.export(output_file, format="wav")
    else:
        audio = audio.set_frame_rate(44100).set_sample_width(2)
        audio.export(output_file, format="wav")

def ask_question(question, question_num, lang_code):
    tts = gTTS(text=question, lang=lang_code)
    question_filename = f"question_{question_num}.wav"
    tts.save(question_filename)
    os.system(f'start {question_filename}')

def record_audio(filename, duration=5, fs=44100):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=2,
                    rate=fs,
                    input=True,
                    frames_per_buffer=1024)

    print("Recording...")

    frames = []

    for _ in range(0, int(fs / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)

    print("Recording finished.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(2)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()

def recognize_speech(filename, lang_code):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language=lang_code)
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return None

def clean_response(response_text, question):
    # Ensure the response doesn't include the question
    if response_text.lower().startswith(question.lower()):
        response_text = response_text[len(question):].strip()
    return response_text

def ask_questions_from_json(data, lang_code, google_code, json_file):
    translator = Translator()
    question_num = 0

    for section, fields in data.items():
        for field, content in fields.items():
            question = content["question"]
            translated_question = translator.translate(question, dest=google_code).text if google_code != 'en' else question
            
            # Ask the question
            print(f"Asking question: {question}")
            ask_question(translated_question, question_num, google_code)
            
            # Wait for the question to finish playing before recording the answer
            print("Answer the question after the prompt finishes...")
            
            # Record the response
            response_filename = f"response_{question_num}.wav"
            record_audio(response_filename, duration=5)
            
            # Convert the recorded response to PCM format
            pcm_response_filename = f"response_{question_num}_pcm.wav"
            convert_to_pcm(response_filename, pcm_response_filename)
            
            # Convert speech to text from the PCM format file
            response_text = recognize_speech(pcm_response_filename, google_code)
            
            if response_text:
                # Clean the response to remove the question part if included
                cleaned_response = clean_response(response_text, question)
                content["response"] = cleaned_response
                print(f"Response recorded: {cleaned_response}")
                
                if google_code != 'en':
                    translated_response = translator.translate(cleaned_response, dest='en').text
                    print(f"Translated response to English: {translated_response}\n")
                else:
                    print(f"Response in English: {cleaned_response}\n")
                
                # Update the JSON file with the response
                with open(json_file, 'w') as file:
                    json.dump(data, file, indent=4)
            else:
                print(f"Could not understand the response for question {question_num+1}")
            
            question_num += 1

    return data

def main():
    translator = Translator()
    print("Choose your language:")
    for key, value in LANGUAGE_OPTIONS.items():
        print(f"{key}: {value[0].capitalize()}")

    choice = input("Enter the number corresponding to your language choice: ")
    if choice not in LANGUAGE_OPTIONS:
        print("Invalid choice, defaulting to English.")
        lang_code, google_code = 'en', 'en'
    else:
        lang_code, google_code = LANGUAGE_OPTIONS[choice]

    # Path to the JSON template
    json_file = 'template.json'
    
    # Load the JSON data
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Ask questions from JSON and capture responses
    ask_questions_from_json(data, lang_code, google_code, json_file)

if __name__ == "__main__":
    main()
