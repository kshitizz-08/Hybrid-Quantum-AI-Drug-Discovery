import httpx

r = httpx.post('http://localhost:8000/api/auth/login', json={'email': 'usera@test.com', 'password': 'password123'})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

exp = httpx.post('http://localhost:8000/api/experiments', json={'name': 'Full Flow Test'}, headers=headers)
exp_id = exp.json()['id']

# ADMET
a = httpx.post(f'http://localhost:8000/api/experiments/{exp_id}/admet?top_n_input=50', headers=headers, timeout=30)
print('ADMET POST:', a.status_code, '| fallback:', a.json().get('fallback_used'), '| screened:', a.json().get('total_screened'))

# GET ADMET
g = httpx.get(f'http://localhost:8000/api/experiments/{exp_id}/admet?limit=3', headers=headers)
print('ADMET GET:', g.status_code, '| total:', g.json().get('total_filtered'), '| returned:', g.json().get('returned'))

# Quantum
q = httpx.post(f'http://localhost:8000/api/experiments/{exp_id}/quantum', json={'k': 5, 'top_n_admet_input': 50}, headers=headers, timeout=30)
print('Quantum POST:', q.status_code, '| status:', q.json().get('status'))

# Ranking
rank = httpx.post(f'http://localhost:8000/api/experiments/{exp_id}/ranking', json={}, headers=headers, timeout=15)
data = rank.json()
print('Ranking POST:', rank.status_code, '| n_ranked:', data.get('n_candidates_ranked'))
for c in data.get('candidates', [])[:3]:
    print(f'  rank={c["rank"]} id={c["molecule_chembl_id"]} score={c["final_score"]}')
