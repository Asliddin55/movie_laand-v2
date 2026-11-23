<?php
/**
 * Movie Land Ultra — MyXvest Native PHP Live SQLite API
 * Reads database.db directly in WAL mode alongside main.py with zero external dependencies.
 */
declare(strict_types=1);

error_reporting(0);
ini_set('display_errors', '0');

$action = isset($_GET['action']) ? trim((string)$_GET['action']) : 'bootstrap';

// Helper: Read BOT_TOKEN securely from .env or config.py (never returned to client)
function ml_get_bot_token(): string {
    static $cached = null;
    if ($cached !== null) return $cached;

    $envPath = __DIR__ . '/.env';
    if (is_file($envPath)) {
        $lines = @file($envPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if (is_array($lines)) {
            foreach ($lines as $line) {
                $line = trim($line);
                if ($line === '' || $line[0] === '#') continue;
                if (strpos($line, 'BOT_TOKEN=') === 0) {
                    $val = trim(substr($line, 10), " \t\n\r\0\x0B\"'");
                    if ($val !== '') return $cached = $val;
                }
            }
        }
    }

    $cfgPath = __DIR__ . '/config.py';
    if (is_file($cfgPath)) {
        $src = (string)@file_get_contents($cfgPath);
        if (preg_match('/BOT_TOKEN\s*=\s*os\.getenv\([^,]+,\s*["\']([^"\']+)["\']\)/', $src, $m)) {
            return $cached = $m[1];
        }
        if (preg_match('/BOT_TOKEN\s*=\s*["\']([^"\']+)["\']/', $src, $m)) {
            return $cached = $m[1];
        }
    }
    return $cached = '';
}

// Helper: Open SQLite DB safely alongside running Python bot
function ml_get_pdo(): ?PDO {
    $dbPath = __DIR__ . '/database.db';
    if (!is_file($dbPath)) return null;
    try {
        $pdo = new PDO('sqlite:' . $dbPath, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec('PRAGMA busy_timeout = 15000;');
        return $pdo;
    } catch (Throwable $e) {
        return null;
    }
}

// Helper: Fetch JSON POST body
function ml_json_body(): array {
    $raw = (string)file_get_contents('php://input');
    if ($raw === '') return $_POST;
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : [];
}

// Helper: Output JSON response
function ml_json(array $data, int $status = 200): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    $flags = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES;
    if (defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
        $flags |= JSON_INVALID_UTF8_SUBSTITUTE;
    }
    $out = json_encode($data, $flags);
    echo ($out !== false) ? $out : '{"ok":false,"error":"json_encode_failed"}';
    exit;
}

// Helper: Official Telegram WebApp initData HMAC-SHA256 verification
function ml_verify_init_data(string $initData): ?array {
    if ($initData === '') return null;
    $botToken = ml_get_bot_token();
    if ($botToken === '') return null;

    parse_str($initData, $params);
    if (!is_array($params) || empty($params['hash'])) return null;

    $receivedHash = (string)$params['hash'];
    unset($params['hash']);
    ksort($params);

    $pairs = [];
    foreach ($params as $k => $v) {
        $pairs[] = $k . '=' . $v;
    }
    $dataCheckString = implode("\n", $pairs);
    $secretKey = hash_hmac('sha256', $botToken, 'WebAppData', true);
    $calcHash = hash_hmac('sha256', $dataCheckString, $secretKey);

    if (!hash_equals($calcHash, $receivedHash)) {
        return null;
    }

    if (isset($params['auth_date']) && ctype_digit((string)$params['auth_date'])) {
        $age = time() - (int)$params['auth_date'];
        if ($age > 86400 * 7) {
            return null;
        }
    }

    if (!empty($params['user'])) {
        $u = json_decode((string)$params['user'], true);
        if (is_array($u)) return $u;
    }
    return $params;
}

// Helper: Normalize photo_id into browser-loadable HTTPS/relative URL
function ml_resolve_photo_url(?string $raw): string {
    $raw = trim((string)$raw);
    if ($raw === '') return '';
    if (preg_match('#^https?://#i', $raw)) {
        return $raw;
    }
    if (strpos($raw, 'uploads/') === 0) {
        return $raw;
    }
    return 'api.php?action=img&fid=' . rawurlencode($raw);
}

// Helper: Multibyte-safe lowercase & substring (works even without mbstring extension!)
function ml_lower(string $s): string {
    return function_exists('mb_strtolower') ? mb_strtolower($s, 'UTF-8') : strtolower($s);
}

function ml_contains(string $haystack, string $needle): bool {
    if (function_exists('mb_strpos')) {
        return mb_strpos($haystack, $needle, 0, 'UTF-8') !== false;
    }
    return strpos($haystack, $needle) !== false;
}

// Helper: Clean genre token into [icon, cleanName]
function ml_split_genre(string $rawGenre): array {
    $g = trim($rawGenre);
    if ($g === '') return ['🎬', 'Boshqa'];
    // Strip leading emojis / pictographs
    $clean = trim((string)preg_replace('/^[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{FE0F}\x{200D}\s]+/u', '', $g));
    if ($clean === '') $clean = $g;

    $iconMap = [
        'jangari' => '🔥',
        'sarguzasht' => '🧭',
        'drama' => '🎭',
        'fantastika' => '🚀',
        'fantaziya' => '🐉',
        'triller' => '🔪',
        'kriminal' => '🕵️',
        'komediya' => '😂',
        'oilaviy' => '👨‍👩‍👧',
        'melodrama' => '💕',
        'multfilm' => '🧸',
        'dahshat' => '👻',
        'qorqinchli' => '👻',
        'detektiv' => '🔍',
        'tarixiy' => '🏛️',
        'harbiy' => '⚔️',
        'anime' => '🎌',
        'serial' => '📺',
        'hujjatli' => '📽️',
        'sport' => '🏆',
        'musiqiy' => '🎵',
        'sirli' => '🔮',
    ];
    $low = ml_lower($clean);
    $icon = '🎬';
    foreach ($iconMap as $k => $ic) {
        if (ml_contains($low, $k)) {
            $icon = $ic;
            break;
        }
    }
    return [$icon, $clean];
}

// ==================== ACTION: IMG PROXY (Telegram file_id -> cached JPEG) ====================
if ($action === 'img') {
    $fid = trim((string)($_GET['fid'] ?? ''));
    if ($fid === '' || strlen($fid) > 200 || !preg_match('/^[A-Za-z0-9_\-]+$/', $fid)) {
        http_response_code(400);
        exit;
    }
    $cacheDir = __DIR__ . '/uploads/posters';
    if (!is_dir($cacheDir)) {
        @mkdir($cacheDir, 0755, true);
    }
    $cacheFile = $cacheDir . '/tg_' . md5($fid) . '.jpg';
    if (is_file($cacheFile) && filesize($cacheFile) > 512) {
        header('Content-Type: image/jpeg');
        header('Cache-Control: public, max-age=2592000');
        readfile($cacheFile);
        exit;
    }

    $token = ml_get_bot_token();
    if ($token === '') {
        http_response_code(404);
        exit;
    }

    $ctx = stream_context_create(['http' => ['timeout' => 10, 'ignore_errors' => true]]);
    $metaRaw = @file_get_contents('https://api.telegram.org/bot' . $token . '/getFile?file_id=' . rawurlencode($fid), false, $ctx);
    $meta = $metaRaw ? json_decode($metaRaw, true) : null;
    if (!is_array($meta) || empty($meta['ok']) || empty($meta['result']['file_path'])) {
        http_response_code(404);
        exit;
    }
    $filePath = $meta['result']['file_path'];
    $imgBytes = @file_get_contents('https://api.telegram.org/file/bot' . $token . '/' . $filePath, false, $ctx);
    if ($imgBytes === false || strlen($imgBytes) < 100) {
        http_response_code(404);
        exit;
    }
    @file_put_contents($cacheFile, $imgBytes);
    header('Content-Type: image/jpeg');
    header('Cache-Control: public, max-age=2592000');
    echo $imgBytes;
    exit;
}

// ==================== ACTION: EPISODES ====================
if ($action === 'episodes') {
    $code = trim((string)($_GET['code'] ?? ''));
    if ($code === '') ml_json(['ok' => false, 'episodes' => []], 400);
    $pdo = ml_get_pdo();
    if (!$pdo) ml_json(['ok' => true, 'episodes' => []]);
    try {
        $stmt = $pdo->prepare('SELECT episode_num, title FROM episodes WHERE movie_code = ? ORDER BY episode_num ASC');
        $stmt->execute([$code]);
        $rows = $stmt->fetchAll();
        ml_json(['ok' => true, 'episodes' => $rows]);
    } catch (Throwable $e) {
        ml_json(['ok' => true, 'episodes' => []]);
    }
}

// ==================== ACTION: AUTH (Telegram WebApp InitData) ====================
if ($action === 'auth') {
    $body = ml_json_body();
    $initData = (string)($body['initData'] ?? '');
    $tgUser = ml_verify_init_data($initData);
    if (!$tgUser || empty($tgUser['id'])) {
        ml_json(['ok' => false, 'error' => 'invalid_signature'], 401);
    }

    $uid = (int)$tgUser['id'];
    $fullName = trim(((string)($tgUser['first_name'] ?? '')) . ' ' . ((string)($tgUser['last_name'] ?? '')));
    if ($fullName === '') $fullName = 'Foydalanuvchi';
    $username = (string)($tgUser['username'] ?? '');
    $photoUrl = (string)($tgUser['photo_url'] ?? '');

    $profile = [
        'id' => $uid,
        'full_name' => $fullName,
        'username' => $username,
        'photo_url' => $photoUrl,
        'joined_at' => date('Y-m-d'),
        'balance' => 0,
        'ref_count' => 0,
        'role' => 'user',
        'is_premium' => false,
        'premium_until' => '',
        'vip_tag' => 'PREMIUM',
        'favorites' => [],
    ];

    $pdo = ml_get_pdo();
    if ($pdo) {
        try {
            $stmt = $pdo->prepare('SELECT full_name, username, joined_at, balance, ref_count, role, is_premium, premium_until, vip_tag FROM users WHERE user_id = ?');
            $stmt->execute([$uid]);
            $u = $stmt->fetch();
            if ($u) {
                if (!empty($u['full_name'])) $profile['full_name'] = (string)$u['full_name'];
                if (!empty($u['username'])) $profile['username'] = (string)$u['username'];
                if (!empty($u['joined_at'])) $profile['joined_at'] = (string)$u['joined_at'];
                $profile['balance'] = (int)($u['balance'] ?? 0);
                $profile['ref_count'] = (int)($u['ref_count'] ?? 0);
                $profile['role'] = (string)($u['role'] ?? 'user');
                $profile['vip_tag'] = (string)($u['vip_tag'] ?? 'PREMIUM');
                $until = (string)($u['premium_until'] ?? '');
                $profile['premium_until'] = $until;
                $isPrem = ((int)($u['is_premium'] ?? 0) === 1);
                if ($isPrem && $until !== '') {
                    $ts = strtotime($until);
                    if ($ts !== false && $ts < time()) {
                        $isPrem = false;
                    }
                }
                $profile['is_premium'] = $isPrem;
            }
            $fStmt = $pdo->prepare('SELECT movie_code FROM favorites WHERE user_id = ?');
            $fStmt->execute([$uid]);
            $favRows = $fStmt->fetchAll();
            $profile['favorites'] = array_map(function ($r) {
                return (string)$r['movie_code'];
            }, $favRows);
        } catch (Throwable $e) {
            // fallback gracefully
        }
    }
    ml_json(['ok' => true, 'user' => $profile]);
}

// ==================== ACTION: TOGGLE FAVORITE ====================
if ($action === 'toggle_fav') {
    $body = ml_json_body();
    $initData = (string)($body['initData'] ?? '');
    $code = trim((string)($body['code'] ?? ''));
    $tgUser = ml_verify_init_data($initData);
    if (!$tgUser || empty($tgUser['id'])) {
        ml_json(['ok' => false, 'error' => 'unauthorized'], 401);
    }
    if ($code === '') {
        ml_json(['ok' => false, 'error' => 'missing_code'], 400);
    }
    $uid = (int)$tgUser['id'];
    $pdo = ml_get_pdo();
    if (!$pdo) {
        ml_json(['ok' => false, 'error' => 'db_unavailable'], 500);
    }
    try {
        $chk = $pdo->prepare('SELECT 1 FROM favorites WHERE user_id = ? AND movie_code = ?');
        $chk->execute([$uid, $code]);
        if ($chk->fetch()) {
            $del = $pdo->prepare('DELETE FROM favorites WHERE user_id = ? AND movie_code = ?');
            $del->execute([$uid, $code]);
            ml_json(['ok' => true, 'is_fav' => false]);
        } else {
            $ins = $pdo->prepare('INSERT OR IGNORE INTO favorites (user_id, movie_code) VALUES (?, ?)');
            $ins->execute([$uid, $code]);
            ml_json(['ok' => true, 'is_fav' => true]);
        }
    } catch (Throwable $e) {
        ml_json(['ok' => false, 'error' => 'db_write_failed'], 500);
    }
}

// ==================== ACTION: BOOTSTRAP (Default Live Catalog + Config + Genres + Trailers) ====================
$settings = [
    'webapp_enabled' => '1',
    'webapp_title' => 'Movie Land',
    'webapp_subtitle' => "O'zbek tilidagi kinolar • 24/7",
    'webapp_banner' => '',
    'vip_7_price' => '7000',
    'vip_30_price' => '20000',
    'vip_90_price' => '30000',
    'ref_reward_amount' => '1000',
];

$movies = [];
$trailers = [];
$pdo = ml_get_pdo();

if ($pdo) {
    try {
        $sRows = $pdo->query('SELECT key, value FROM settings')->fetchAll();
        foreach ($sRows as $sr) {
            $settings[(string)$sr['key']] = (string)$sr['value'];
        }
        // Increment WebApp visits counter gently
        try {
            $curV = (int)($settings['webapp_visits'] ?? '0');
            $upd = $pdo->prepare("INSERT OR REPLACE INTO settings (key, value) VALUES ('webapp_visits', ?)");
            $upd->execute([(string)($curV + 1)]);
        } catch (Throwable $ignored) {}
    } catch (Throwable $ignored) {}

    try {
        $sql = "
            SELECT m.code, m.name, m.genre, m.year, m.country, m.language,
                   m.quality, m.imdb, m.views, m.photo_id, m.caption, m.is_serial,
                   (SELECT COUNT(*) FROM episodes e WHERE e.movie_code = m.code) AS ep_cnt
            FROM movies m
            ORDER BY CAST(m.code AS INTEGER) DESC, m.rowid DESC
            LIMIT 1000
        ";
        $rows = $pdo->query($sql)->fetchAll();
        foreach ($rows as $r) {
            $epCnt = max(1, (int)($r['ep_cnt'] ?? 0));
            $movies[] = [
                'code' => (string)$r['code'],
                'name' => (string)$r['name'],
                'genre' => (string)($r['genre'] ?: '🔥 Jangari'),
                'year' => (string)($r['year'] ?: '2024'),
                'country' => (string)($r['country'] ?: 'AQSH'),
                'language' => (string)($r['language'] ?: "O'zbek tilida"),
                'quality' => (string)($r['quality'] ?: '1080p Full HD'),
                'imdb' => (string)($r['imdb'] ?: '8.4'),
                'views' => (int)($r['views'] ?? 0),
                'photo_id' => ml_resolve_photo_url($r['photo_id'] ?? ''),
                'caption' => (string)($r['caption'] ?? ''),
                'is_serial' => (int)($r['is_serial'] ?? 0),
                'episodes_count' => $epCnt,
            ];
        }
    } catch (Throwable $ignored) {}

    try {
        $tRows = $pdo->query('SELECT id, title, poster_url, video_url, year, badge FROM webapp_trailers ORDER BY id DESC LIMIT 30')->fetchAll();
        foreach ($tRows as $tr) {
            $badge = trim((string)($tr['badge'] ?? 'Tez kunda'));
            $yr = trim((string)($tr['year'] ?? ''));
            $note = $yr !== '' ? ($badge . ' • ' . $yr) : $badge;
            $trailers[] = [
                'id' => (int)$tr['id'],
                'title' => (string)$tr['title'],
                'poster_url' => ml_resolve_photo_url($tr['poster_url'] ?? ''),
                'video_url' => (string)($tr['video_url'] ?? ''),
                'year' => $yr,
                'badge' => $badge,
                'release_note' => $note,
            ];
        }
    } catch (Throwable $ignored) {}
}

// Fallback to webapp/catalog.json if SQLite had 0 movies but static JSON exists
if (empty($movies) && is_file(__DIR__ . '/webapp/catalog.json')) {
    $rawJson = @file_get_contents(__DIR__ . '/webapp/catalog.json');
    $parsed = $rawJson ? json_decode($rawJson, true) : null;
    if (is_array($parsed) && !empty($parsed['movies']) && is_array($parsed['movies'])) {
        $movies = $parsed['movies'];
    }
}

// Build live Genres catalog with counts & up to 4 poster thumbnails per genre for fanned collage cards
$genreMap = [];
$serialCount = 0;
foreach ($movies as $m) {
    if (!empty($m['is_serial'])) $serialCount++;
    $parts = preg_split('/[,•|\/]+/', (string)$m['genre']);
    if (!is_array($parts)) $parts = [$m['genre']];
    $seenLocal = [];
    foreach ($parts as $rawPart) {
        $rawPart = trim($rawPart);
        if ($rawPart === '') continue;
        [$icon, $cleanName] = ml_split_genre($rawPart);
        $key = ml_lower($cleanName);
        if (isset($seenLocal[$key])) continue;
        $seenLocal[$key] = true;
        if (!isset($genreMap[$key])) {
            $genreMap[$key] = [
                'key' => $key,
                'name' => $cleanName,
                'icon' => $icon,
                'count' => 0,
                'posters' => [],
            ];
        }
        $genreMap[$key]['count']++;
        if (!empty($m['photo_id']) && count($genreMap[$key]['posters']) < 4) {
            if (!in_array($m['photo_id'], $genreMap[$key]['posters'], true)) {
                $genreMap[$key]['posters'][] = $m['photo_id'];
            }
        }
    }
}

// Ensure default rich genre list exists even on a freshly cleaned DB
if (empty($genreMap)) {
    $defaults = [
        ['🔥', 'Jangari'], ['🧭', 'Sarguzasht'], ['🎭', 'Drama'],
        ['🚀', 'Fantastika'], ['🐉', 'Fantaziya'], ['🔪', 'Triller'],
        ['🕵️', 'Kriminal'], ['😂', 'Komediya'], ['👨‍👩‍👧', 'Oilaviy'],
        ['💕', 'Melodrama'], ['🧸', 'Multfilm'], ['👻', 'Dahshat'],
    ];
    foreach ($defaults as [$ic, $nm]) {
        $k = ml_lower($nm);
        $genreMap[$k] = ['key' => $k, 'name' => $nm, 'icon' => $ic, 'count' => 0, 'posters' => []];
    }
}

$genres = array_values($genreMap);
usort($genres, static function (array $a, array $b): int {
    if ($b['count'] !== $a['count']) return $b['count'] <=> $a['count'];
    return strcmp($a['name'], $b['name']);
});

ml_json([
    'ok' => true,
    'config' => [
        'webapp_enabled' => $settings['webapp_enabled'] ?? '1',
        'webapp_title' => $settings['webapp_title'] ?: 'Movie Land',
        'webapp_subtitle' => $settings['webapp_subtitle'] ?: "O'zbek tilidagi kinolar • 24/7",
        'webapp_banner' => $settings['webapp_banner'] ?? '',
        'vip_7_price' => (int)($settings['vip_7_price'] ?: 7000),
        'vip_30_price' => (int)($settings['vip_30_price'] ?: 20000),
        'vip_90_price' => (int)($settings['vip_90_price'] ?: 30000),
        'ref_reward_amount' => (int)($settings['ref_reward_amount'] ?: 1000),
        'bot_username' => 'movieeland_bot',
        'channel_url' => 'https://t.me/movieee_land',
        'group_url' => 'https://t.me/movieeland_group',
    ],
    'stats' => [
        'total_movies' => count($movies),
        'total_serials' => $serialCount,
        'total_genres' => count($genres),
    ],
    'movies' => $movies,
    'genres' => $genres,
    'trailers' => $trailers,
]);
