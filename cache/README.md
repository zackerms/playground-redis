# Cache
## Get Started
```
docker compose up -d
```

## 負荷テスト
```bash
docker compose run k6 run /scripts/no-cache.js

docker compose run k6 run /scripts/cache-hit.js

docker compose run k6 run /scripts/mixed-operations.js
```

| ファイル名          | シナリオ                                   |
| ------------------- | ------------------------------------------ |
| no-cache.js         | キャッシュがない状態でのユーザー検索       |
| cache-hit.js        | 同じユーザーの連続検索（キャッシュヒット） |
| mixed-operations.js | 書き込みと読み取りの混合テスト             |