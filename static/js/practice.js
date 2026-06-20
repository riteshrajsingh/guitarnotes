// Tiny localStorage practice tracker. Each feature page can call
// GuitarPractice.record(featureId, xp) to log a session.
// Storage shape:
//   { totalXp: number,
//     days: { 'YYYY-MM-DD': { totalXp: number, byFeature: {id: xp} } },
//     features: { id: { totalXp, lastSession } } }
window.GuitarPractice = (function () {
    const KEY = 'guitarPracticeV1';

    function load() {
        try {
            const raw = localStorage.getItem(KEY);
            if (!raw) return { totalXp: 0, days: {}, features: {} };
            const parsed = JSON.parse(raw);
            return Object.assign({ totalXp: 0, days: {}, features: {} }, parsed);
        } catch (e) {
            return { totalXp: 0, days: {}, features: {} };
        }
    }

    function save(state) {
        localStorage.setItem(KEY, JSON.stringify(state));
    }

    function todayKey() {
        const d = new Date();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${d.getFullYear()}-${m}-${day}`;
    }

    function record(featureId, xp) {
        if (!featureId || !xp) return;
        const state = load();
        const day = todayKey();
        state.totalXp = (state.totalXp || 0) + xp;
        if (!state.days[day]) state.days[day] = { totalXp: 0, byFeature: {} };
        state.days[day].totalXp += xp;
        state.days[day].byFeature[featureId] = (state.days[day].byFeature[featureId] || 0) + xp;
        if (!state.features[featureId]) state.features[featureId] = { totalXp: 0, lastSession: null };
        state.features[featureId].totalXp += xp;
        state.features[featureId].lastSession = new Date().toISOString();
        save(state);
    }

    function get() {
        return load();
    }

    function reset() {
        localStorage.removeItem(KEY);
    }

    function streak() {
        const state = load();
        const days = Object.keys(state.days).sort();
        if (days.length === 0) return 0;
        let count = 0;
        const d = new Date();
        for (;;) {
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const k = `${d.getFullYear()}-${m}-${day}`;
            if (state.days[k]) {
                count++;
                d.setDate(d.getDate() - 1);
            } else {
                // Allow today to be empty without breaking yesterday's streak.
                if (count === 0 && k === todayKey()) {
                    d.setDate(d.getDate() - 1);
                    continue;
                }
                break;
            }
        }
        return count;
    }

    function levelFromXp(totalXp) {
        // 100 xp = lvl 1->2, 250 to 3, 500 to 4, doubling roughly each level.
        const tiers = [
            { name: 'Open Chord Apprentice',  min: 0 },
            { name: 'String Wrangler',        min: 100 },
            { name: 'Fretboard Explorer',     min: 300 },
            { name: 'CAGED Initiate',         min: 700 },
            { name: 'Mode Conjurer',          min: 1500 },
            { name: 'Tone Architect',         min: 3000 },
            { name: 'Six-String Sage',        min: 6000 },
        ];
        let level = 1, current = tiers[0];
        for (let i = 0; i < tiers.length; i++) {
            if (totalXp >= tiers[i].min) {
                level = i + 1;
                current = tiers[i];
            }
        }
        const next = tiers[level] || null;
        return { level, name: current.name, currentMin: current.min, nextMin: next ? next.min : null };
    }

    return { record, get, reset, streak, levelFromXp, todayKey };
})();
