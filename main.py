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


@app.template_filter('songfmt')
def render_song_content(content):
    """Render song content as a <pre> block with section / chord / lyric spans."""
    if not content:
        return Markup('')
    out = []
    for line in content.split('\n'):
        sec = SECTION_RE.match(line)
        if sec:
            out.append(f'<span class="song-section">[{escape(sec.group(1))}]</span>')
        elif is_chord_line(line):
            out.append(f'<span class="song-chords">{escape(line)}</span>')
        elif line.strip() == '':
            out.append('')
        else:
            out.append(f'<span class="song-lyric">{escape(line)}</span>')
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


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5001)
