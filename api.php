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

// Helper: Read exact default VIP/referral values from config.py so WebApp ALWAYS matches Bot 100%
function ml_read_config_defaults(): array {
    static $defs = null;
    if ($defs !== null) return $defs;
    $defs = [
        'vip_7_price' => '10000',
        'vip_30_price' => '25000',
        'vip_90_price' => '60000',
        'ref_reward_amount' => '1500',
        'daily_reward_amount' => '1000',
    ];
    $cfgPath = __DIR__ . '/config.py';
    if (is_file($cfgPath)) {
        $src = (string)@file_get_contents($cfgPath);
        $map = [
            'DEFAULT_VIP_7_PRICE' => 'vip_7_price',
            'DEFAULT_VIP_30_PRICE' => 'vip_30_price',
            'DEFAULT_VIP_90_PRICE' => 'vip_90_price',
            'DEFAULT_REF_REWARD' => 'ref_reward_amount',
            'DEFAULT_DAILY_REWARD' => 'daily_reward_amount',
        ];
        foreach ($map as $pyName => $key) {
            if (preg_match('/' . $pyName . '\s*=\s*["\'](\d+)["\']/', $src, $m)) {
                $defs[$key] = $m[1];
            }
        }
    }
    return $defs;
}

// Helper: Normalize text for smart AI search
function ml_norm_text(string $s): string {
    $t = ml_lower($s);
    $t = str_replace(["ʻ", "‘", "’", "`", "ʼ", "'"], '', $t);
    $t = (string)preg_replace('/[^\p{L}\p{N}\s]+/u', ' ', $t);
    return trim((string)preg_replace('/\s+/', ' ', $t));
}

// Helper: Send quick Telegram notification after WebApp VIP purchase
function ml_tg_notify(int $chatId, string $htmlText): void {
    $token = ml_get_bot_token();
    if ($token === '' || $chatId <= 0) return;
    $payload = http_build_query([
        'chat_id' => $chatId,
        'text' => $htmlText,
        'parse_mode' => 'HTML',
    ]);
    $ctx = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/x-www-form-urlencoded\r\n",
            'content' => $payload,
            'timeout' => 4,
            'ignore_errors' => true,
        ],
    ]);
    @file_get_contents('https://api.telegram.org/bot' . $token . '/sendMessage', false, $ctx);
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

// ==================== ACTION: BUY VIP DIRECTLY FROM BALANCE (100% SYNCED WITH BOT) ====================
if ($action === 'buy_vip') {
    $body = ml_json_body();
    $initData = (string)($body['initData'] ?? '');
    $days = (int)($body['days'] ?? 30);
    if (!in_array($days, [7, 30, 90], true)) {
        ml_json(['ok' => false, 'error' => 'invalid_plan'], 400);
    }
    $tgUser = ml_verify_init_data($initData);
    if (!$tgUser || empty($tgUser['id'])) {
        ml_json(['ok' => false, 'error' => 'unauthorized'], 401);
    }
    $uid = (int)$tgUser['id'];
    $pdo = ml_get_pdo();
    if (!$pdo) {
        ml_json(['ok' => false, 'error' => 'db_unavailable'], 500);
    }

    $defs = ml_read_config_defaults();
    $priceKey = $days === 7 ? 'vip_7_price' : ($days === 90 ? 'vip_90_price' : 'vip_30_price');
    $price = (int)$defs[$priceKey];
    try {
        $pStmt = $pdo->prepare('SELECT value FROM settings WHERE key = ?');
        $pStmt->execute([$priceKey]);
        $pRow = $pStmt->fetch();
        if ($pRow && is_numeric($pRow['value'])) {
            $price = (int)$pRow['value'];
        }
    } catch (Throwable $ignored) {}

    try {
        $pdo->beginTransaction();
        $uStmt = $pdo->prepare('SELECT balance, is_premium, premium_until, vip_tag FROM users WHERE user_id = ?');
        $uStmt->execute([$uid]);
        $u = $uStmt->fetch();
        if (!$u) {
            $pdo->rollBack();
            ml_json(['ok' => false, 'error' => 'user_not_found', 'needed' => $price, 'price' => $price, 'balance' => 0], 404);
        }
        $bal = (int)($u['balance'] ?? 0);
        if ($bal < $price) {
            $pdo->rollBack();
            ml_json([
                'ok' => false,
                'error' => 'insufficient_balance',
                'needed' => $price - $bal,
                'price' => $price,
                'balance' => $bal,
            ], 400);
        }

        $nowTs = time();
        $baseTs = $nowTs;
        $curUntil = (string)($u['premium_until'] ?? '');
        if ((int)($u['is_premium'] ?? 0) === 1 && $curUntil !== '') {
            $parsedTs = strtotime($curUntil);
            if ($parsedTs !== false && $parsedTs > $nowTs) {
                $baseTs = $parsedTs;
            }
        }
        $newUntil = gmdate('Y-m-d\TH:i:s', $baseTs + ($days * 86400));
        $newBal = $bal - $price;
        $vipTag = !empty($u['vip_tag']) ? (string)$u['vip_tag'] : 'PREMIUM';

        $upd = $pdo->prepare('UPDATE users SET balance = ?, is_premium = 1, premium_until = ? WHERE user_id = ?');
        $upd->execute([$newBal, $newUntil, $uid]);
        $pdo->commit();

        $fmtPrice = number_format($price, 0, '.', ' ');
        $fmtBal = number_format($newBal, 0, '.', ' ');
        ml_tg_notify(
            $uid,
            "🎉 <b>TABRIKLAYMIZ! WEBAPP ORQALI PREMIUM (VIP) FAOLLASHTIRILDI!</b>\n"
            . "━━━━━━━━━━━━━━━━━━\n"
            . "💎 <b>Paket:</b> {$days} kunlik VIP ({$fmtPrice} so'm)\n"
            . "📅 <b>Amal qiladi:</b> <code>" . substr($newUntil, 0, 10) . "</code> gacha\n"
            . "🏷 <b>VIP Teg:</b> <code>[{$vipTag}]</code>\n"
            . "💰 <b>Qolgan balans:</b> {$fmtBal} so'm"
        );

        ml_json([
            'ok' => true,
            'days' => $days,
            'price' => $price,
            'new_balance' => $newBal,
            'premium_until' => $newUntil,
            'vip_tag' => $vipTag,
            'is_premium' => true,
        ]);
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        ml_json(['ok' => false, 'error' => 'purchase_failed'], 500);
    }
}

// ==================== ACTION: MOVIE LAND AI CHAT (LIVE SQLITE SMART ENGINE) ====================
if ($action === 'ai_chat') {
    $body = ml_json_body();
    $rawQ = trim((string)($body['query'] ?? ''));
    $pdo = ml_get_pdo();
    $allMovies = [];

    if ($pdo) {
        try {
            $rows = $pdo->query("
                SELECT m.code, m.name, m.genre, m.year, m.country, m.quality, m.imdb, m.views, m.photo_id, m.caption, m.is_serial,
                       (SELECT COUNT(*) FROM episodes e WHERE e.movie_code = m.code) AS ep_cnt
                FROM movies m
                ORDER BY CAST(m.code AS INTEGER) DESC
                LIMIT 1000
            ")->fetchAll();
            foreach ($rows as $r) {
                $allMovies[] = [
                    'code' => (string)$r['code'],
                    'name' => (string)$r['name'],
                    'genre' => (string)($r['genre'] ?: '🔥 Jangari'),
                    'year' => (string)($r['year'] ?: '2024'),
                    'country' => (string)($r['country'] ?: 'AQSH'),
                    'quality' => (string)($r['quality'] ?: '1080p Full HD'),
                    'imdb' => (string)($r['imdb'] ?: '8.4'),
                    'views' => (int)($r['views'] ?? 0),
                    'photo_id' => ml_resolve_photo_url($r['photo_id'] ?? ''),
                    'caption' => (string)($r['caption'] ?? ''),
                    'is_serial' => (int)($r['is_serial'] ?? 0),
                    'episodes_count' => max(1, (int)($r['ep_cnt'] ?? 0)),
                ];
            }
        } catch (Throwable $ignored) {}
    }

    if (empty($allMovies) && is_file(__DIR__ . '/webapp/catalog.json')) {
        $parsed = json_decode((string)@file_get_contents(__DIR__ . '/webapp/catalog.json'), true);
        if (is_array($parsed) && !empty($parsed['movies'])) $allMovies = $parsed['movies'];
    }

    if (empty($allMovies)) {
        ml_json(['ok' => true, 'reply' => "🤖 Movie Land AI: Hozircha katalog to'ldirilmoqda. Tez orada eng sara kinolar qo'shiladi!", 'movies' => []]);
    }

    $qLow = ml_lower($rawQ);
    $qNorm = ml_norm_text($rawQ);
    $greetings = ['salom', 'assalom', 'privet', 'hello', 'hi', 'yordam', 'help'];
    $words = array_values(array_filter(explode(' ', $qNorm)));
    if ($rawQ === '' || (count($words) <= 2 && count(array_intersect($words, $greetings)) > 0)) {
        usort($allMovies, static function ($a, $b) { return ($b['views'] ?? 0) <=> ($a['views'] ?? 0); });
        ml_json([
            'ok' => true,
            'reply' => "Assalomu alaykum! Men — Movie Land AI yordamchisiman. Kayfiyatingiz, janr, yil yoki syujetni yozing (masalan: «kulgili kino», «sehrgar haqida serial», «2024 jangari») — bazamizdan eng zo'rlarini topib beraman!",
            'movies' => array_slice($allMovies, 0, 6),
        ]);
    }

    $intentGenres = [
        'jangari' => ['jangari', 'urush', 'otishma', 'jang', 'qasos', 'politsiya', 'snayper', 'boevik', 'action', 'marvel', 'superqahramon'],
        'komediya' => ['komediya', 'kulgili', 'kulgi', 'hazil', 'quvnoq', 'comedy', 'prikol'],
        'fantastika' => ['fantastika', 'fantaziya', 'sehr', 'sehrgar', 'kosmos', 'robot', 'kelajak', 'ajdar', 'marvel', 'dc'],
        'qorqinchli' => ['qorqinchli', 'ujas', 'dahshat', 'triller', 'zombi', 'jin', 'arvoh', 'horror'],
        'drama' => ['drama', 'dramma', 'hayotiy', 'tasirli', 'yiglatadigan'],
        'melodrama' => ['melodrama', 'sevgi', 'muhabbat', 'romantik', 'romantika'],
        'multfilm' => ['multfilm', 'multik', 'bolalar', 'oilaviy', 'hayvon', 'animatsiya'],
        'detektiv' => ['detektiv', 'sirli', 'jinoyat', 'kriminal', 'tergov'],
        'tarixiy' => ['tarixiy', 'qadimiy', 'qirol', 'ritsar', 'imperiya', 'jangchi'],
        'anime' => ['anime', 'yapon'],
    ];
    $stop = ['menga','uchun','kino','kinolar','film','topib','ber','bering','tavsiya','qil','zor','yaxshi','eng','bir','bitta','qaysi','nima','bor','haqida','bilan','yoki','korish','kerak','qidir'];

    $wantsSerial = false;
    foreach (['serial', 'qismli', 'fasl', 'sezon', 'epizod'] as $sk) {
        if (ml_contains($qNorm, $sk)) { $wantsSerial = true; break; }
    }
    $wantsTop = false;
    foreach (['top', 'mashhur', 'eng zor', 'eng yaxshi', 'reyting', 'imdb'] as $tk) {
        if (ml_contains($qNorm, $tk)) { $wantsTop = true; break; }
    }
    $wantsNew = false;
    foreach (['yangi', 'premyera', 'oxirgi'] as $nk) {
        if (ml_contains($qNorm, $nk)) { $wantsNew = true; break; }
    }

    $targetYear = '';
    if (preg_match('/\b(19\d{2}|20\d{2})\b/', $rawQ, $ym)) {
        $targetYear = $ym[1];
    }

    $matchedGenres = [];
    foreach ($intentGenres as $gk => $kws) {
        foreach ($kws as $kw) {
            if (ml_contains($qNorm, $kw)) { $matchedGenres[] = $gk; break; }
        }
    }

    $tokens = array_values(array_filter($words, static function ($w) use ($stop) {
        return strlen($w) >= 3 && !in_array($w, $stop, true);
    }));

    $scored = [];
    foreach ($allMovies as $m) {
        $sc = 0.0;
        $mNameN = ml_norm_text($m['name']);
        $mGenN = ml_norm_text($m['genre']);
        $mCapN = ml_norm_text($m['caption']);
        $mCtrN = ml_norm_text($m['country']);
        $mYr = (string)$m['year'];
        $views = (int)$m['views'];
        $imdb = (float)str_replace(',', '.', (string)$m['imdb']);

        if (ltrim($qNorm, '#') === (string)$m['code']) $sc += 120.0;
        if ($qNorm !== '' && strlen($qNorm) >= 3) {
            if ($qNorm === $mNameN) $sc += 100.0;
            elseif (ml_contains($mNameN, $qNorm) || (strlen($mNameN) >= 4 && ml_contains($qNorm, $mNameN))) $sc += 65.0;
        }
        foreach ($tokens as $tok) {
            if (ml_contains($mNameN, $tok)) $sc += 24.0;
            if (ml_contains($mCapN, $tok)) $sc += 10.0;
            if (ml_contains($mGenN, $tok)) $sc += 14.0;
            if (ml_contains($mCtrN, $tok)) $sc += 12.0;
        }
        foreach ($matchedGenres as $gk) {
            if (ml_contains($mGenN, $gk)) $sc += 28.0;
        }
        if ($wantsSerial) $sc += !empty($m['is_serial']) ? 36.0 : -15.0;
        if ($targetYear !== '') {
            if ($mYr === $targetYear) $sc += 30.0;
            elseif (ctype_digit($mYr) && abs((int)$mYr - (int)$targetYear) <= 1) $sc += 12.0;
        }
        if ($wantsTop) $sc += min($views / 80.0, 20.0) + ($imdb * 2.5);
        if ($wantsNew && ctype_digit($mYr) && (int)$mYr >= 2023) $sc += 20.0;
        $sc += min($views / 500.0, 4.0) + ($imdb * 0.4);
        $scored[] = ['score' => $sc, 'movie' => $m];
    }

    usort($scored, static function ($a, $b) { return $b['score'] <=> $a['score']; });
    $picked = [];
    foreach (array_slice($scored, 0, 6) as $row) {
        if ($row['score'] >= 14.0 || count($picked) < 4) {
            $picked[] = $row['movie'];
        }
    }

    $reply = "«{$rawQ}» so'rovingiz bo'yicha bazamizdan eng mos " . count($picked) . " ta film/serialni tanlab berdim. Istalgan kartochkani bosib darhol tomosha qilishingiz mumkin!";
    ml_json(['ok' => true, 'reply' => $reply, 'movies' => $picked]);
}

// ==================== ACTION: BOOTSTRAP (Default Live Catalog + Config + Genres + Trailers) ====================
$cfgDefs = ml_read_config_defaults();
$settings = [
    'webapp_enabled' => '1',
    'webapp_title' => 'Movie Land',
    'webapp_subtitle' => "O'zbek tilidagi kinolar • 24/7",
    'webapp_banner' => '',
    'vip_7_price' => $cfgDefs['vip_7_price'],
    'vip_30_price' => $cfgDefs['vip_30_price'],
    'vip_90_price' => $cfgDefs['vip_90_price'],
    'ref_reward_amount' => $cfgDefs['ref_reward_amount'],
    'daily_reward_amount' => $cfgDefs['daily_reward_amount'],
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
        'vip_7_price' => (int)($settings['vip_7_price'] ?: $cfgDefs['vip_7_price']),
        'vip_30_price' => (int)($settings['vip_30_price'] ?: $cfgDefs['vip_30_price']),
        'vip_90_price' => (int)($settings['vip_90_price'] ?: $cfgDefs['vip_90_price']),
        'ref_reward_amount' => (int)($settings['ref_reward_amount'] ?: $cfgDefs['ref_reward_amount']),
        'daily_reward_amount' => (int)($settings['daily_reward_amount'] ?: $cfgDefs['daily_reward_amount']),
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
