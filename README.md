# Niko-Onegen

Chat with an AI Niko from OneShot using Pygame and Google Gemini!

## What it Does

* Talk with an AI Niko.
* See Niko's expressions change.
* Text appears character-by-character.
* Includes sound effects.
* Customize backgrounds, faces, and sounds.
* Easy first-time setup.
* In-game menu for options (volume, text speed, etc.).
* See your chat history.
* Drag the window to move it.

## Getting Started

**Requirements:**

* Python 3.9+
* Pygame, Google Generative AI, Pydantic, Python-dotenv tkinter (`pip install pygame google-genai pydantic python-dotenv tkinter`)

**Setup:**

1. **Clone:** `git clone <repository_url> && cd niko-onegen`
2. **Install:** `pip install -r requirements.txt` (or install manually from the list above).
3. **API Key:**

* Rename `.env.example` to `.env`.
* Paste your Google AI Studio API key into `.env`. Get one [here](https://aistudio.google.com/app/apikey).

    ```dotenv
    # .env
    GOOGLE_API_KEY=YOUR_API_KEY_HERE
    ```

## Running It

```bash
python main.py
```

* The first time you run it, a setup guide will appear.
* Press `TAB` or `ESC` anytime to open the options menu.

## Configuration & Customization

* **Settings:** Your choices (name, speed, volume, background) are saved in `options.json` after the first run. Use the in-game menu (`TAB`/`ESC`) to change them later.
* **AI Personality:** You can tweak how Niko talks by editing `INITIAL_PROMPT` in `config.py` (be careful!).
* **Custom Stuff:**
* **Faces:** Add `niko_*.png` images to `res/faces/`.
* **Sounds:** Add `.wav`/`.ogg`/`.mp3` files to `res/sfx/`.
* **Backgrounds:** Add `.png`/`.jpg`/`.jpeg` images to `res/backgrounds/`.
* *(Optional)* Update `config.py` if you want the AI to know about new faces or sounds.

## License

This project is under MIT, basically almost open source.
