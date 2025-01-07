from flask import Flask, render_template, request

app = Flask(__name__)

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
    for capo in sorted(common_keys):
        progression_chords = [capo_dict[progression][capo] for progression in capo_dict]
        results.append(f"Capo on {capo}: " + ", ".join(progression_chords))
    return results

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/scales')
def scales():
    return render_template('scales.html')

@app.route("/capo-transpose", methods=["GET", "POST"])
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

@app.route('/chord-library')
def chord_library():
    return render_template('chord-library.html')


if __name__ == "__main__":
    app.run(debug=True)
