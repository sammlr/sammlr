"""Read-only routes for synthetic candidates. No request command exists."""
from flask import Blueprint, abort, render_template, render_template_string
from pathlib import Path
from .fixtures import CANDIDATES

preview = Blueprint('pax', __name__, url_prefix='/pax')


@preview.get('/')
def discovery():
    return render_template('pax/discovery.html', candidates=CANDIDATES)


@preview.get('/<candidate_id>')
def detail(candidate_id):
    item = next((c for c in CANDIDATES if c['id'] == candidate_id), None)
    if item is None:
        abort(404)
    return render_template('pax/detail.html', candidate=item)


@preview.get('/layer-comparison')
def layer_comparison():
    """Read-only visual experiment; never persists or chooses a cap."""
    return render_template_string((Path(__file__).parent / 'layer_comparison.html').read_text())
