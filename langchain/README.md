Cli:
`python main.py cli`
Mode Api:
`python main.py api`

health Check
curl http://localhost:8000/

# Ask Question
'''
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: PujanggaTSDUU@2$$%!!!" \
  -d '{"question": "What menu items do you have?"}'
'''

# Refresh Cache
'''
curl -X POST "http://localhost:8000/refresh" \
  -H "X-API-Key: rahasia-kuat-123456"
'''

# Check Cache stats
'''
curl "http://localhost:8000/cache/stats" \
  -H "X-API-Key: rahasia-kuat-123456"
'''