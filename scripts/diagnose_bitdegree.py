"""Reconsulta pública reproduzível das seis missões auditadas; não envia Telegram."""
import argparse
import json
from pathlib import Path
from src.bitdegree_quizzes import public_client
from src.quiz_analyzer import extract_public_questions
from src.quiz_diagnostics import diagnose
from src.utils import atomic_json, digest, utcnow


def audit(entries, client):
    result = []
    for entry in entries:
        item = {'title':entry['title'], 'url':entry['url'], 'checked_at':utcnow().isoformat(),
                'http_status':None, 'content_type':None, 'questions_extracted':0,
                'questions_analyzed':0, 'conclusive_answers':0}
        try:
            body, final, content_type = client.get(entry['url'], ['www.bitdegree.org'])
            item.update(http_status=200, content_type=content_type, final_url=final)
            if 'html' not in content_type:
                raise ValueError('unexpected_content_type')
            questions = extract_public_questions(body, final)
            item.update(diagnostic=diagnose(body, final), questions_extracted=len(questions),
                        body_hash=digest(body.decode('utf-8', errors='replace')))
            # Auditoria de extração apenas; respostas não são inferidas da descrição promocional.
        except Exception as exc:
            records = getattr(client, 'records', [])
            if isinstance(records, list) and records:
                item.update(http_status=records[-1].get('status'), content_type=records[-1].get('content_type'))
            item['diagnostic'] = {'reason_code':'technical_collection_failure', 'error_type':type(exc).__name__}
        result.append(item)
    return {'version':'2.2', 'mode':'public_extraction_audit_no_submission', 'missions':result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/bitdegree-diagnostic.json'))
    args = parser.parse_args()
    entries = json.loads(Path('config/bitdegree_diagnostic_missions.json').read_text())
    atomic_json(args.output, audit(entries, public_client()))


if __name__ == '__main__':
    main()
