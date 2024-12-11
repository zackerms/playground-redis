import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '20s', target: 10 },
        { duration: '30s', target: 10 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<1000'],  // キャッシュなしの場合は閾値を緩める
    },
};

const BASE_URL = 'http://api:8000';

// テスト用のユーザーメールアドレス配列（10件）
const TEST_USERS = Array.from({ length: 10 }, (_, i) => ({
    email: `test_${i}@example.com`,
    name: `Test User ${i}`
}));

// セットアップ - テストユーザーの作成
export function setup() {
    TEST_USERS.forEach(user => {
        http.post(`${BASE_URL}/users/`, JSON.stringify(user), {
            headers: { 'Content-Type': 'application/json' }
        });
    });
    return { users: TEST_USERS };
}

// メインシナリオ - ランダムなユーザー検索
export default function(data) {
    // ランダムなユーザーを選択
    const randomUser = data.users[Math.floor(Math.random() * data.users.length)];
    
    const res = http.get(`${BASE_URL}/users/${randomUser.email}`, {
        tags: { type: 'no_cache_search' }
    });

    check(res, {
        'ユーザー検索が成功': (r) => r.status === 200,
        'レスポンスに正しいメールアドレスが含まれる': (r) => {
            const body = JSON.parse(r.body);
            return body.email === randomUser.email;
        }
    });

    sleep(1);
}