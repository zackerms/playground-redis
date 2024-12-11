import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '20s', target: 10 },
        { duration: '30s', target: 10 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<100'],  // キャッシュヒットの場合は厳しい閾値
    },
};

const BASE_URL = 'http://api:8000';
const FIXED_TEST_USER = {
    email: 'cache_test@example.com',
    name: 'Cache Test User'
};

// セットアップ - 固定テストユーザーの作成
export function setup() {
    const res = http.post(`${BASE_URL}/db/users/`, JSON.stringify(FIXED_TEST_USER), {
        headers: { 'Content-Type': 'application/json' }
    });
    
    check(res, {
        'テストユーザーの作成が成功': (r) => r.status === 200
    });

    return { testUser: FIXED_TEST_USER };
}

// メインシナリオ - 同一ユーザーの連続検索
export default function(data) {
    const res = http.get(`${BASE_URL}/db/users/${data.testUser.email}`, {
        tags: { type: 'cache_hit_search' }
    });

    check(res, {
        'キャッシュからのユーザー検索が成功': (r) => r.status === 200,
        'レスポンスに正しいメールアドレスが含まれる': (r) => {
            const body = JSON.parse(r.body);
            return body.email === data.testUser.email;
        }
    });

    sleep(0.1); // キャッシュヒットのケースは短いインターバル
}