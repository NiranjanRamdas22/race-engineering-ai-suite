"""Source-backed shipped examples and facts-only report generation."""
from pathlib import Path
import json
RACES_DATABASE=json.loads((Path(__file__).resolve().parents[4]/"data/race-fixtures.json").read_text(encoding="utf-8"))

def generate_analytical_debrief(race):
    """A facts-only debrief. Generated causal interpretation is not implied."""
    lines=[f"# Race Debrief: {race['name']}",f"Venue: {race['circuit']}","Record: "+("incomplete" if race.get('incomplete',True) else "complete supplied results"),"Supplied facts are reproduced below; timeline descriptions are supplied annotations, not independently inferred causes."]
    winner=race.get('winner')
    lines += ['## Results',f"Winner: {winner['driver']}" if winner else 'Winner: unknown']
    for p in race.get('podium',[]):lines.append(f"- P{p.get('pos','?')}: {p['driver']} ({p.get('team') or 'team unknown'}) — {p.get('gap') or 'gap unknown'}")
    if race.get('fastest_lap'):lines.append('Fastest lap (supplied): '+str(race['fastest_lap']))
    if race.get('strategy_stints'):
        lines.append('## Supplied tyre stints')
        for s in race['strategy_stints']:lines.append(f"- {s['driver']}: "+' → '.join(s['stints']))
    strategy=[e for e in race.get('key_timeline',[]) if e['type'] in ('STRATEGY','WEATHER','PIT_STOP','PIT_CYCLE_GAIN','ON_TRACK_OVERTAKE','RETIREMENT_INHERITANCE','FLAG','RETIREMENT','POSITION_CHANGE')]
    if strategy:
        lines.append('## Critical Strategic Decisions')
        for e in strategy:lines.append(f"- Lap {e['lap']} · {e['type']} · {e['title']}: {e['description']}")
    if race.get('key_timeline'):
        lines.append('## Chronological timeline')
        for e in race['key_timeline']:lines.append(f"- Lap {e['lap']} · {e['type']} · {e['title']}: {e['description']}")
    if race.get('sources'):
        lines.append('## Sources and evidence limits')
        for source in race['sources']:lines.append(f"- {source['label']}: {source.get('url') or 'User supplied'} — {source.get('scope','Supplied facts')}")
    return '\n\n'.join(lines)
