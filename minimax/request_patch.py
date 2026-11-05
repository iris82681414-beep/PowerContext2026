"""Request a reviewable loan.py proposal from the official MiniMax API."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('context', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default=os.environ.get('MINIMAX_MODEL'))
    parser.add_argument('--region', choices=('cn', 'global'), default='cn')
    args = parser.parse_args()
    if not args.model:
        parser.error('Select a MiniMax model available to your account with --model or MINIMAX_MODEL')
    api_key = os.environ.get('MINIMAX_CN_API_KEY' if args.region == 'cn' else 'MINIMAX_API_KEY')
    if not api_key:
        parser.error('Set the MiniMax API key for the selected region in the process environment')
    context = json.loads(args.context.read_text(encoding='utf-8'))
    sources = context.get('sources', [])
    paths = {source['path'] for source in sources}
    if not {'policy.md', 'loan.py', 'test_loan.py'} <= paths:
        parser.error('Use sdd.py prepare to retrieve the specification, source, and test')
    for source in sources:
        if hashlib.sha256(source['body'].encode()).hexdigest() != source['digest']:
            parser.error('The context source digest does not match its body')
    args.output.mkdir(parents=True, exist_ok=False)
    messages = [
        {'role': 'system', 'content': 'You are implementing the supplied loan-renewal task. '
         'Use the retrieved specification and preserve the public function signature and tests. '
         'Return only a JSON object with one string field named code containing the entire new loan.py. '
         'Do not include analysis, markdown fences, or other files.'},
        {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)},
    ]
    payload = {'model': args.model, 'messages': messages, 'stream': False,
               'max_completion_tokens': 4096, 'reasoning_split': True}
    (args.output / 'request.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    host = 'api.minimaxi.com' if args.region == 'cn' else 'api.minimax.io'
    request = Request('https://' + host + '/v1/chat/completions',
                      data=json.dumps(payload).encode(),
                      headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f'MiniMax returned HTTP {error.code}') from None
    except URLError:
        raise RuntimeError('Could not reach the MiniMax API') from None
    if result.get('base_resp', {}).get('status_code', 0) != 0:
        raise RuntimeError('MiniMax returned an API error')
    if not result.get('id') or not isinstance(result.get('model'), str):
        raise RuntimeError('MiniMax response is missing its response ID or model')
    choice = result['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise RuntimeError('MiniMax did not finish the code response')
    answer = choice['message']['content']
    if '<think>' in answer or '</think>' in answer:
        raise RuntimeError('MiniMax did not separate its reasoning from the code response')
    proposal = json.loads(answer)
    code = proposal['code']
    if not isinstance(code, str) or len(code.encode()) > 16_384:
        raise ValueError('Expected a Python source proposal of at most 16 KiB')
    ast.parse(code, filename='proposed-loan.py')
    metadata = {name: result.get(name) for name in ('id', 'model', 'created', 'usage')}
    metadata.update(finish_reason=choice['finish_reason'], content=answer,
                    provider_host=host,
                    context_sha256=hashlib.sha256(args.context.read_bytes()).hexdigest(),
                    request_sha256=hashlib.sha256((args.output / 'request.json').read_bytes()).hexdigest(),
                    proposal_sha256=hashlib.sha256(code.encode('utf-8')).hexdigest())
    (args.output / 'response.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / 'proposed-loan.py').write_text(code, encoding='utf-8')
    print('Saved proposal and API evidence. Review the proposed file before applying it to fixture/loan.py.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, IndexError, SyntaxError) as error:
        detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f'Patch request failed: {detail}', file=sys.stderr)
        sys.exit(1)
