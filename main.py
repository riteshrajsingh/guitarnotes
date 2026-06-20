from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, abort, flash
from markupsafe import Markup, escape
from functools import wraps
import os
import json
import re

app = Flask(__name__, static_url_path='/static', static_folder='static')
# Required for Flask sessions / flash messages. Override in production via env var.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
ADMIN_PASSWORD = os.environ.get("GUITAR_ADMIN_PASSWORD", "guitar")
SONGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs.json")

CHROMATIC_SCALE = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#',
                   'A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
CHROMATIC_SCALE_MINOR = ['Am', 'A#m', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m',
                         'Am', 'A#m', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m']
CHROMATIC_SCALE_MINOR.reverse()
CHROMATIC_SCALE.reverse()

OPEN_CHORDS_MAJOR = ['A', 'C', 'D', 'E', 'G', 'F']
OPEN_CHORDS_MINOR = ['Am', 'Dm', 'Em']

def get_minor_capo_position(input_chord):
    capo_details = {}
    input_index = CHROMATIC_SCALE_MINOR.index(input_chord)
    for chord in OPEN_CHORDS_MINOR:
        capo_position = CHROMATIC_SCALE_MINOR.index(chord, input_index) - input_index
        capo_details[capo_position] = chord
    return capo_details

def get_major_capo_position(input_chord):
    capo_details = {}
    input_index = CHROMATIC_SCALE.index(input_chord)
    for chord in OPEN_CHORDS_MAJOR:
        capo_position = CHROMATIC_SCALE.index(chord, input_index) - input_index
        capo_details[capo_position] = chord
    return capo_details


def get_capo_patterns(input_chord_progression):
    capo_dict = {}

    # Populate capo_dict with mappings of input chords to their possible capo transpositions
    for input_chord in input_chord_progression:
        if input_chord.endswith("m"):
            capo_positions = get_minor_capo_position(input_chord)
        else:
            capo_positions = get_major_capo_position(input_chord)
        capo_dict[input_chord] = capo_positions  # Store mappings

    # Find common capo positions among all chords
    keys_list = [set(capo_dict_item.keys()) for capo_dict_item in capo_dict.values()]
    common_keys = set.intersection(*keys_list)

    if not common_keys:
        return ["No common capo positions found."]

    results = []

    # Build a more informative output
    for capo in sorted(common_keys):
        progression_chords = [
            f"{original} → {capo_dict[original][capo]}"
            for original in capo_dict
        ]
        results.append(f"Capo on {capo}: " + "; ".join(progression_chords))

    return results



def get_capo_patterns_old(input_chord_progression):
    capo_dict = {}
    for input_chord in input_chord_progression:
        if input_chord.endswith("m"):
            capo_positions = get_minor_capo_position(input_chord)
            capo_dict[input_chord] = capo_positions
        else:
            capo_positions = get_major_capo_position(input_chord)
            capo_dict[input_chord] = capo_positions

    keys_list = [set(capo_dict_item.keys()) for capo_dict_item in capo_dict.values()]
    common_keys = set.intersection(*keys_list)

    if not common_keys:
        return ["No common capo positions found."]

    results = []
    print(capo_dict)
    for capo in sorted(common_keys):
        progression_chords = [capo_dict[progression][capo] for progression in capo_dict]
        results.append(f"Capo on {capo}: " + ", ".join(progression_chords))
    return results

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/guitar')
@app.route('/guitar/')
def guitar_landing():
    return render_template('main.html')

@app.route('/guitar/scales')
def scales():
    return render_template('scales.html')

@app.route('/guitar-samples/<string:string_folder>/<path:filename>')
def serve_guitar_sample(string_folder, filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(base_dir, 'guitar-samples')
    relative_file_path = os.path.join(string_folder, filename)

    try:
        return send_from_directory(samples_dir, relative_file_path)
    except FileNotFoundError:
        return "Sample not found", 404

@app.route('/guitar/ear-training')
def ear_training():
    return render_template('ear_training.html')

@app.route('/guitar/chord-ear-training')
def chord_ear_training():
    return render_template('chord_ear_training.html')

@app.route('/guitar/fretboard-trainer')
def fretboard_trainer():
    return render_template('fretboard_trainer.html')

@app.route('/guitar/interval-trainer')
def interval_trainer():
    return render_template('interval_trainer.html')

@app.route('/guitar/chord-progression')
def chord_progression():
    return render_template('chord_progression.html')

@app.route('/guitar/find-the-key')
def find_the_key():
    return render_template('find_the_key.html')

@app.route('/guitar/tuner')
def tuner():
    return render_template('tuner.html')

@app.route('/guitar/strum-trainer')
def strum_trainer():
    return render_template('strum_trainer.html')

@app.route('/guitar/chord-speed-drill')
def chord_speed_drill():
    return render_template('chord_speed_drill.html')

@app.route('/guitar/backing-jam')
def backing_jam():
    return render_template('backing_jam.html')

@app.route('/guitar/tab-reader')
def tab_reader():
    return render_template('tab_reader.html')

@app.route('/guitar/practice-streak')
def practice_streak():
    return render_template('practice_streak.html')

@app.route('/guitar/audio-to-tab')
def audio_to_tab():
    return render_template('audio_to_tab.html')

@app.route('/guitar/identify_notes')
def identify_notes():
    return render_template('identify_notes.html')

@app.route("/guitar/capo-transpose", methods=["GET", "POST"])
def capo_transposer():
    capo_positions = None
    selected_chords = None
    if request.method == "POST":
        selected_chords = request.form.getlist("chords")
        if not selected_chords:
            error = "Please select at least one chord."
            return render_template("main.html", error=error)
        capo_positions = get_capo_patterns(selected_chords)
    return render_template("capo-transpose.html", capo_positions=capo_positions, selected_chords=selected_chords)

@app.route('/guitar/chord-library')
def chord_library():
    return render_template('chord-library.html')


# ===== Song Book =====
# Public list/view, password-gated admin (add/edit/delete). Songs persist to
# songs.json in the project directory.

CHORD_TOKEN_RE = re.compile(
    r'^[A-G][#b]?'                  # root
    r'(?:m|maj|min|dim|aug)?'        # quality
    r'(?:\d{1,2})?'                  # extension number (7, 11, 13)
    r'(?:sus\d?)?'                   # suspension
    r'(?:add\d{1,2})?'               # added tone
    r'(?:/[A-G][#b]?)?'              # bass note
    r'$'
)
SECTION_RE = re.compile(r'^\s*\[(.+)\]\s*$')
SLUG_STRIP_RE = re.compile(r'[^a-zA-Z0-9\s-]')
SLUG_DASH_RE = re.compile(r'[\s-]+')


def load_songs():
    if not os.path.exists(SONGS_FILE):
        return []
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f).get('songs', [])


def save_songs(songs):
    tmp = SONGS_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'songs': songs}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SONGS_FILE)


def find_song(songs, song_id):
    return next((s for s in songs if s.get('id') == song_id), None)


def slugify(text):
    text = SLUG_STRIP_RE.sub('', text or '').strip().lower()
    text = SLUG_DASH_RE.sub('-', text)
    return text or 'song'


def unique_slug(base, existing_ids):
    slug = base
    n = 2
    while slug in existing_ids:
        slug = f"{base}-{n}"
        n += 1
    return slug


def is_chord_line(line):
    tokens = line.split()
    if not tokens:
        return False
    return all(CHORD_TOKEN_RE.match(t) for t in tokens)


# Open-position chords most beginners learn first.
EASY_CHORDS = {'C', 'D', 'G', 'A', 'E', 'Am', 'Em', 'Dm'}
# Common barre / sus chords — typical "second-step" difficulty.
MEDIUM_CHORDS = {'F', 'Bm', 'B', 'F#m', 'Fm', 'C#m', 'G#m', 'Bb', 'F#', 'Eb', 'Ab', 'Db'}


def extract_chords(content):
    if not content:
        return []
    found = []
    for line in content.split('\n'):
        if is_chord_line(line):
            for tok in line.split():
                found.append(tok)
    return found


def classify_song_difficulty(content):
    """Tag a song Easy / Medium / Hard based on the chords it uses.

    - Easy: only open-position major/minor chords (C, D, G, A, E, Am, Em, Dm).
    - Medium: includes barre or sus chords, but no extensions.
    - Hard: any 7ths, extensions, slash chords, diminished/augmented, etc.
    """
    chords = extract_chords(content)
    if not chords:
        return 'Easy'
    has_extension = False
    has_medium = False
    only_easy = True
    for c in chords:
        # Strip slash bass for the difficulty check on the main chord.
        main = c.split('/')[0]
        # Anything with a digit, sus, dim, aug, maj is at least medium/hard.
        if any(tok in c for tok in ('7', '9', '11', '13', 'maj', 'dim', 'aug', 'add')):
            has_extension = True
            only_easy = False
            continue
        if 'sus' in main:
            has_medium = True
            only_easy = False
            continue
        if main in EASY_CHORDS:
            continue
        if main in MEDIUM_CHORDS:
            has_medium = True
            only_easy = False
        else:
            # Unknown chord — treat conservatively as medium.
            has_medium = True
            only_easy = False
        # Slash chord with a non-trivial bass nudges difficulty up.
        if '/' in c:
            has_medium = True
            only_easy = False
    if has_extension:
        return 'Hard'
    if has_medium:
        return 'Medium'
    return 'Easy' if only_easy else 'Medium'


def annotate_songs(songs):
    for s in songs:
        s['difficulty'] = classify_song_difficulty(s.get('content', ''))
    return songs


@app.template_filter('songfmt')
def render_song_content(content):
    """Render song content as one <div> per line, classified as section /
    chord / lyric / blank. Each line is its own block so 'hide chords' can
    fully remove chord lines (no empty gaps left behind)."""
    if not content:
        return Markup('')
    out = []
    for line in content.split('\n'):
        sec = SECTION_RE.match(line)
        if sec:
            out.append(f'<div class="song-section">[{escape(sec.group(1))}]</div>')
        elif is_chord_line(line):
            out.append(f'<div class="song-chords">{escape(line)}</div>')
        elif line.strip() == '':
            out.append('<div class="song-blank">&nbsp;</div>')
        else:
            out.append(f'<div class="song-lyric">{escape(line)}</div>')
    return Markup('\n'.join(out))


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('songs_login', next=request.url))
        return f(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_admin_flag():
    return {'is_admin': bool(session.get('is_admin'))}


@app.route('/guitar/songs')
def songs_list():
    songs = sorted(load_songs(), key=lambda s: s.get('title', '').lower())
    annotate_songs(songs)
    return render_template('songs_list.html', songs=songs)


@app.route('/guitar/songs/login', methods=['GET', 'POST'])
def songs_login():
    error = None
    next_url = request.values.get('next') or url_for('songs_admin')
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(next_url)
        error = 'Incorrect password.'
    return render_template('songs_login.html', error=error, next=next_url)


@app.route('/guitar/songs/logout')
def songs_logout():
    session.pop('is_admin', None)
    return redirect(url_for('songs_list'))


@app.route('/guitar/songs/admin')
@admin_required
def songs_admin():
    songs = sorted(load_songs(), key=lambda s: s.get('title', '').lower())
    return render_template('songs_admin.html', songs=songs, song=None)


@app.route('/guitar/songs/admin/new', methods=['POST'])
@admin_required
def songs_admin_new():
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Title is required.')
        return redirect(url_for('songs_admin'))
    songs = load_songs()
    sid = unique_slug(slugify(title), {s['id'] for s in songs})
    songs.append({
        'id': sid,
        'title': title,
        'artist': (request.form.get('artist') or '').strip(),
        'key': (request.form.get('key') or '').strip(),
        'capo': (request.form.get('capo') or '').strip(),
        'content': request.form.get('content') or '',
    })
    save_songs(songs)
    return redirect(url_for('song_view', song_id=sid))


@app.route('/guitar/songs/admin/<song_id>', methods=['GET', 'POST'])
@admin_required
def songs_admin_edit(song_id):
    songs = load_songs()
    song = find_song(songs, song_id)
    if not song:
        abort(404)
    if request.method == 'POST':
        new_title = (request.form.get('title') or '').strip()
        if new_title:
            song['title'] = new_title
        song['artist'] = (request.form.get('artist') or '').strip()
        song['key'] = (request.form.get('key') or '').strip()
        song['capo'] = (request.form.get('capo') or '').strip()
        song['content'] = request.form.get('content') or ''
        save_songs(songs)
        return redirect(url_for('song_view', song_id=song_id))
    all_songs = sorted(songs, key=lambda s: s.get('title', '').lower())
    return render_template('songs_admin.html', songs=all_songs, song=song)


@app.route('/guitar/songs/admin/<song_id>/delete', methods=['POST'])
@admin_required
def songs_admin_delete(song_id):
    songs = load_songs()
    songs = [s for s in songs if s.get('id') != song_id]
    save_songs(songs)
    return redirect(url_for('songs_admin'))


@app.route('/guitar/songs/<song_id>')
def song_view(song_id):
    song = find_song(load_songs(), song_id)
    if not song:
        abort(404)
    return render_template('song_view.html', song=song)


# ===== Chord recordings =====
# Per-chord audio recordings used by chord_ear_training.html. The trainer
# falls back to per-string synthesis when a recording is missing.

CHORD_SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chord-samples')

CHORD_TYPES = {
    'Major':        '',
    'Minor':        'm',
    'Diminished':   'dim',
    'Augmented':    'aug',
    'Sus2':         'sus2',
    'Sus4':         'sus4',
    'Major 7':      'maj7',
    'Minor 7':      'm7',
    'Dominant 7':   '7',
    'Diminished 7': 'dim7',
    'Half-Dim 7':   'm7b5',
}
CHORD_ROOTS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHORD_ALLOWED_EXTS = {'mp4', 'm4a', 'webm', 'ogg', 'wav', 'mp3', 'aac'}


def chord_file_base(root, type_name):
    if root not in CHORD_ROOTS or type_name not in CHORD_TYPES:
        return None
    return f"{root.replace('#', 's')}{CHORD_TYPES[type_name]}"


def find_chord_file(base):
    """Return (filename, ext) for an existing recording, or (None, None)."""
    if not os.path.isdir(CHORD_SAMPLES_DIR):
        return None, None
    for ext in CHORD_ALLOWED_EXTS:
        candidate = f"{base}.{ext}"
        if os.path.exists(os.path.join(CHORD_SAMPLES_DIR, candidate)):
            return candidate, ext
    return None, None


def remove_chord_files(base):
    if not os.path.isdir(CHORD_SAMPLES_DIR):
        return
    for ext in CHORD_ALLOWED_EXTS:
        path = os.path.join(CHORD_SAMPLES_DIR, f"{base}.{ext}")
        if os.path.exists(path):
            os.remove(path)


def chord_samples_index():
    out = {}
    if os.path.isdir(CHORD_SAMPLES_DIR):
        for root in CHORD_ROOTS:
            for type_name in CHORD_TYPES:
                base = chord_file_base(root, type_name)
                fname, _ = find_chord_file(base)
                if fname:
                    out[f"{root}|{type_name}"] = url_for('serve_chord_sample', filename=fname)
    return out


@app.route('/chord-samples/<path:filename>')
def serve_chord_sample(filename):
    if '/' in filename or '\\' in filename or filename.startswith('.'):
        abort(404)
    try:
        return send_from_directory(CHORD_SAMPLES_DIR, filename)
    except FileNotFoundError:
        abort(404)


@app.route('/guitar/chord-samples-manifest.json')
def chord_samples_manifest():
    return chord_samples_index()


@app.route('/guitar/chord-recorder')
@admin_required
def chord_recorder():
    return render_template(
        'chord_recorder.html',
        roots=CHORD_ROOTS,
        types=list(CHORD_TYPES.keys()),
        suffixes=CHORD_TYPES,
        existing=chord_samples_index(),
    )


@app.route('/guitar/chord-recorder/upload', methods=['POST'])
@admin_required
def chord_recorder_upload():
    root = request.form.get('root', '')
    type_name = request.form.get('type', '')
    base = chord_file_base(root, type_name)
    if not base:
        return {'error': 'invalid root or type'}, 400
    file = request.files.get('audio')
    if not file or not file.filename:
        return {'error': 'no audio file uploaded'}, 400
    ext = (request.form.get('ext') or os.path.splitext(file.filename)[1].lstrip('.') or '').lower()
    if ext not in CHORD_ALLOWED_EXTS:
        return {'error': f'unsupported extension: {ext}'}, 400

    os.makedirs(CHORD_SAMPLES_DIR, exist_ok=True)
    remove_chord_files(base)
    filename = f"{base}.{ext}"
    file.save(os.path.join(CHORD_SAMPLES_DIR, filename))
    return {'ok': True, 'url': url_for('serve_chord_sample', filename=filename)}


@app.route('/guitar/chord-recorder/delete', methods=['POST'])
@admin_required
def chord_recorder_delete():
    root = request.form.get('root', '')
    type_name = request.form.get('type', '')
    base = chord_file_base(root, type_name)
    if not base:
        return {'error': 'invalid root or type'}, 400
    remove_chord_files(base)
    return {'ok': True}


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5001)
