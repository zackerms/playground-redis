import http from 'k6/http';
import { check } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

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
        http.post(`${BASE_URL}/db/users/`, JSON.stringify(user), {
            headers: { 'Content-Type': 'application/json' }
        });
    });
    return { users: TEST_USERS };
}

// メインシナリオ - ランダムなユーザーを選択してユーザー名を更新
export default function(data) {
    // ランダムなユーザーを選択
    const randomUser = data.users[Math.floor(Math.random() * data.users.length)];
    const email = randomUser.email;
    const newName = `Updated_${randomString(5)}`;
   
    const res = http.put(
        `${BASE_URL}/db/users/${email}?name=${newName}`,
        null,
        { tags: { type: 'write' } }
    );

    check(res, { 'ユーザー名更新が成功': (r) => r.status === 200 });
}