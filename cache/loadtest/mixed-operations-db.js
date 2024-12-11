import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

export const options = {
    stages: [
        { duration: '20s', target: 10 },
        { duration: '30s', target: 10 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'],
        'http_req_duration{type:write}': ['p(95)<1000'],
        'http_req_duration{type:read}': ['p(95)<300'],
    },
};

const BASE_URL = 'http://api:8000';

// 新規ユーザー作成
function createUser() {
    const payload = {
        name: `User_${randomString(5)}`,
        email: `user_${randomString(5)}@example.com`
    };

    const res = http.post(`${BASE_URL}/db/users/`, JSON.stringify(payload), {
        headers: { 'Content-Type': 'application/json' },
        tags: { type: 'write' }
    });

    check(res, { 'ユーザー作成が成功': (r) => r.status === 200 });
    return payload;
}

// ユーザー名更新
function updateUserName(email) {
    const newName = `Updated_${randomString(5)}`;
    const res = http.put(
        `${BASE_URL}/db/users/${email}?name=${newName}`,
        null,
        { tags: { type: 'write' } }
    );

    check(res, { 'ユーザー名更新が成功': (r) => r.status === 200 });
}

// ユーザー検索
function searchUser(email) {
    const res = http.get(`${BASE_URL}/db/users/${email}`, {
        tags: { type: 'read' }
    });

    check(res, { 'ユーザー検索が成功': (r) => r.status === 200 });
}

// メインシナリオ - 書き込みと読み取りの混合
export default function() {
    const scenario = Math.random();

    if (scenario < 0.3) {  // 30% 新規作成
        const user = createUser();
        sleep(1);
    } else if (scenario < 0.5) {  // 20% 更新
        const user = createUser();  // 更新用のユーザーを作成
        sleep(1);
        updateUserName(user.email);
        sleep(1);
    } else {  // 50% 検索
        const user = createUser();  // 検索用のユーザーを作成
        sleep(1);
        searchUser(user.email);
        sleep(0.5);
    }
}