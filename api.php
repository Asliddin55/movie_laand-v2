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

// Helper: Phonetic + Cyrillic/English/Uzbek fuzzy key ('Garry Poter' / 'Gerry Poter' / 'Гарри Поттер' -> 'gari poter')
function ml_phonetic_key(string $s): string {
    $cyr = [
        'а'=>'a','б'=>'b','в'=>'v','г'=>'g','д'=>'d','е'=>'e','ё'=>'yo','ж'=>'j','з'=>'z',
        'и'=>'i','й'=>'y','к'=>'k','л'=>'l','м'=>'m','н'=>'n','о'=>'o','п'=>'p','р'=>'r',
        'с'=>'s','т'=>'t','у'=>'u','ф'=>'f','х'=>'x','ц'=>'s','ч'=>'ch','ш'=>'sh','щ'=>'sh',
        'ъ'=>'','ы'=>'i','ь'=>'','э'=>'e','ю'=>'yu','я'=>'ya','ў'=>'o','қ'=>'q','ғ'=>'g','ҳ'=>'h',
    ];
    $t = ml_lower($s);
    $t = strtr($t, $cyr);
    $t = str_replace(["ʻ", "‘", "’", "`", "ʼ", "'"], '', $t);
    $t = (string)preg_replace('/[^a-z0-9\s]+/', ' ', $t);
    $t = trim((string)preg_replace('/\s+/', ' ', $t));

    $synonyms = [
        'harry potter' => 'garri potter', 'garry poter' => 'garri potter', 'gerry poter' => 'garri potter',
        'garry potter' => 'garri potter', 'gerry potter' => 'garri potter', 'geri poter' => 'garri potter',
        'gari poter' => 'garri potter', 'potter' => 'garri potter', 'poter' => 'garri potter',
        'spider man' => 'orgimchak odam', 'spiderman' => 'orgimchak odam', 'spaydermen' => 'orgimchak odam',
        'chelovek pauk' => 'orgimchak odam', 'moon knight' => 'oy ritsari', 'lunniy ritsar' => 'oy ritsari',
        'legend of the seeker' => 'iztopar afsonasi', 'legenda ob iskatele' => 'iztopar afsonasi',
        'merlin' => 'afsungar merlin', 'envel' => 'envel qahramonlari', 'creed' => 'krid',
        'paddington' => 'padington', 'cars' => 'chaqmoq makvin', 'mcqueen' => 'chaqmoq makvin',
        'flash' => 'flesh', 'gods of egypt' => 'misr afsonalari', 'kingdom of heaven' => 'muqaddas zamin',
        'noah' => 'nuh', 'kraven' => 'ovchi kreyven', 'john carter' => 'jon karter',
        'fullmetal alchemist' => 'polat alximik', 'sniper' => 'snayper', 'trap' => 'tuzoq',
        'bethoven' => 'beethoven', 'betxoven' => 'beethoven', 'tri bogatirya' => 'uch bahodir',
    ];
    foreach ($synonyms as $alias => $target) {
        if (strpos($t, $alias) !== false) {
            $t = str_replace($alias, $target, $t);
        }
    }
    $t = str_replace(['ph', 'oo', 'ee'], ['f', 'u', 'i'], $t);
    $t = strtr($t, ['y' => 'i', 'q' => 'k', 'c' => 'k', 'w' => 'v', 'h' => 'x']);
    $t = (string)preg_replace('/([a-z])\1+/', '$1', $t);
    return trim((string)preg_replace('/\s+/', ' ', $t));
}

function ml_sim_ratio(string $a, string $b): float {
    if ($a === '' || $b === '') return 0.0;
    if ($a === $b) return 1.0;
    similar_text($a, $b, $pct);
    return $pct / 100.0;
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

// Helper: Clean genre token into [svgIconKey, cleanName] — ZERO corrupt UTF-8 or raw emojis!
function ml_split_genre(string $rawGenre): array {
    $g = str_replace(["\xEF\xBF\xBD", "\xEF\xB8\x8F", "\xEF\xB8\x8E", "\xE2\x80\x8D"], '', $rawGenre);
    // Strip everything except Unicode letters, apostrophes, spaces and hyphens
    $clean = (string)preg_replace('/[^\p{L}\'\’\ʻ\s\-]+/u', ' ', $g);
    $clean = trim((string)preg_replace('/\s+/u', ' ', $clean));
    $clean = trim($clean, " -'’ʻ");
    if ($clean === '' || (function_exists('mb_strlen') ? mb_strlen($clean, 'UTF-8') : strlen($clean)) < 2) {
        return ['', ''];
    }

    $canonMap = [
        'melodrama'  => ['heart',    'Melodrama'],
        'jangari'    => ['flame',    'Jangari'],
        'boevik'     => ['flame',    'Jangari'],
        'action'     => ['flame',    'Jangari'],
        'sarguzasht' => ['compass',  'Sarguzasht'],
        'drama'      => ['masks',    'Drama'],
        'dramma'     => ['masks',    'Drama'],
        'fantastika' => ['rocket',   'Fantastika'],
        'fantaziya'  => ['wand',     'Fantaziya'],
        'triller'    => ['bolt',     'Triller'],
        'kriminal'   => ['shield',   'Kriminal'],
        'komediya'   => ['smile',    'Komediya'],
        'oilaviy'    => ['users',    'Oilaviy'],
        'multfilm'   => ['sparkles', 'Multfilm'],
        'dahshat'    => ['ghost',    "Qo'rqinchli"],
        'qorqinchli' => ['ghost',    "Qo'rqinchli"],
        'detektiv'   => ['search',   'Detektiv'],
        'tarixiy'    => ['landmark', 'Tarixiy'],
        'harbiy'     => ['sword',    'Harbiy'],
        'anime'      => ['star',     'Anime'],
        'serial'     => ['tv',       'Serial'],
        'hujjatli'   => ['film',     'Hujjatli'],
        'sport'      => ['trophy',   'Sport'],
        'musiqiy'    => ['music',    'Musiqiy'],
        'sirli'      => ['eye',      'Sirli'],
        'milliy'     => ['globe',    'Milliy'],
        'biografiya' => ['book',     'Biografiya'],
    ];

    $norm = str_replace(["'", "’", "ʻ", "‘", "`", "ʼ"], '', ml_lower($clean));
    foreach ($canonMap as $k => $pair) {
        if (ml_contains($norm, $k)) {
            return $pair;
        }
    }
    // Capitalize first letter cleanly
    $first = function_exists('mb_strtoupper') ? mb_strtoupper(mb_substr($clean, 0, 1, 'UTF-8'), 'UTF-8') . mb_substr($clean, 1, null, 'UTF-8') : ucfirst($clean);
    return ['film', $first];
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

// ==================== ACTION: MOVIE LAND AI CHAT (GEMINI 2.5 PRO/FLASH + FULL BOT KNOWLEDGE) ====================
if ($action === 'ai_chat') {
    $body = ml_json_body();
    $rawQ = trim((string)($body['query'] ?? ''));
    $initData = (string)($body['initData'] ?? '');
    $historyIn = is_array($body['history'] ?? null) ? $body['history'] : [];
    $pdo = ml_get_pdo();
    $allMovies = [];
    $settingsMap = ml_read_config_defaults();
    $settingsMap['payment_card_info'] = '5614 6820 1538 7808';
    $settingsMap['free_order_limit'] = '2';
    $settingsMap['premium_order_limit'] = '5';
    $settingsMap['webapp_url'] = 'https://6b02fedeb2d06.myxvest1.ru/';
    $settingsMap['ai_enabled'] = '1';
    $settingsMap['ai_active_provider'] = 'gemini';

    if ($pdo) {
        try {
            foreach ($pdo->query('SELECT key, value FROM settings')->fetchAll() as $sr) {
                $settingsMap[(string)$sr['key']] = (string)$sr['value'];
            }
        } catch (Throwable $ignored) {}

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

    // Foydalanuvchi jonli profilini olish (agar initData bo'lsa)
    $userCtx = ['id' => 0, 'name' => 'Mehmon', 'balance' => 0, 'refs' => 0, 'is_vip' => false, 'vip_until' => '', 'vip_tag' => 'PREMIUM'];
    $tgUser = ml_verify_init_data($initData);
    if ($tgUser && !empty($tgUser['id'])) {
        $uid = (int)$tgUser['id'];
        $userCtx['id'] = $uid;
        $userCtx['name'] = trim(((string)($tgUser['first_name'] ?? '')) . ' ' . ((string)($tgUser['last_name'] ?? ''))) ?: 'Foydalanuvchi';
        if ($pdo) {
            try {
                $us = $pdo->prepare('SELECT full_name, balance, ref_count, is_premium, premium_until, vip_tag FROM users WHERE user_id = ?');
                $us->execute([$uid]);
                $uRow = $us->fetch();
                if ($uRow) {
                    if (!empty($uRow['full_name'])) $userCtx['name'] = (string)$uRow['full_name'];
                    $userCtx['balance'] = (int)($uRow['balance'] ?? 0);
                    $userCtx['refs'] = (int)($uRow['ref_count'] ?? 0);
                    $userCtx['vip_tag'] = (string)($uRow['vip_tag'] ?? 'PREMIUM');
                    $until = (string)($uRow['premium_until'] ?? '');
                    $isP = ((int)($uRow['is_premium'] ?? 0) === 1);
                    if ($isP && $until !== '' && strtotime($until) !== false && strtotime($until) < time()) $isP = false;
                    $userCtx['is_vip'] = $isP;
                    $userCtx['vip_until'] = substr($until, 0, 10);
                }
            } catch (Throwable $ignored) {}
        }
    }

    $qLow = ml_lower($rawQ);
    $qNorm = ml_norm_text($rawQ);
    $words = array_values(array_filter(explode(' ', $qNorm)));

    // Intent aniqlash (VIP, Balans, Buyurtma, Qanday ishlaydi, Salom, Kino)
    $intent = 'movie';
    foreach (['vip', 'premium', 'obuna', 'tarif', 'narx', 'karta', 'tolov', 'chek', 'sotib'] as $kw) {
        if (ml_contains($qNorm, $kw)) { $intent = 'vip'; break; }
    }
    if ($intent === 'movie') {
        foreach (['balans', 'pul ishla', 'referal', 'taklif', 'bonus', 'kunlik', 'dost'] as $kw) {
            if (ml_contains($qNorm, $kw)) { $intent = 'balance'; break; }
        }
    }
    if ($intent === 'movie') {
        foreach (['buyurtma', 'zakaz', 'qoshib ber', 'topolmadim', 'bazada yoq'] as $kw) {
            if (ml_contains($qNorm, $kw)) { $intent = 'order'; break; }
        }
    }
    if ($intent === 'movie') {
        foreach (['qanday ishlaydi', 'qanday qidir', 'nima qila olasan', 'yordam', 'guruh', 'kanal', 'admin', 'qoida', 'webapp'] as $kw) {
            if (ml_contains($qNorm, $kw)) { $intent = 'howto'; break; }
        }
    }
    if ($intent === 'movie' && ($rawQ === '' || (count($words) <= 3 && count(array_intersect($words, ['salom', 'assalom', 'privet', 'hello', 'hi', 'rahmat', 'raxmat'])) > 0))) {
        $intent = 'greeting';
    }

    // Mos kinolarni hisoblash
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
    $stop = ['menga','uchun','kino','kinolar','kinosi','kinosini','film','filmlar','filmi','filmini','topib','ber','bering','tavsiya','qil','qiling','zor','yaxshi','eng','bir','bitta','qaysi','nima','bor','bormi','haqida','bilan','va','yoki','shu','osha','korish','istayman','xohlayman','kerak','qidir','qidiryapman','salom','assalomu','alaykum','iltimos','iltmos','tashla','tashlab','yubor','yuboring','och','ochib','kod','kodi'];
    $wantsSerial = false;
    foreach (['serial', 'qismli', 'fasl', 'sezon', 'epizod'] as $sk) { if (ml_contains($qNorm, $sk)) { $wantsSerial = true; break; } }
    $wantsTop = (bool)preg_match('/\btop\b/u', $qNorm);
    if (!$wantsTop) {
        foreach (['mashhur', 'eng zor', 'eng yaxshi', 'reyting', 'imdb'] as $tk) { if (ml_contains($qNorm, $tk)) { $wantsTop = true; break; } }
    }
    $wantsNew = false;
    foreach (['yangi', 'premyera', 'oxirgi'] as $nk) { if (ml_contains($qNorm, $nk)) { $wantsNew = true; break; } }
    $targetYear = '';
    if (preg_match('/\b(19\d{2}|20\d{2})\b/', $rawQ, $ym)) $targetYear = $ym[1];

    $matchedGenres = [];
    foreach ($intentGenres as $gk => $kws) {
        foreach ($kws as $kw) { if (ml_contains($qNorm, $kw)) { $matchedGenres[] = $gk; break; } }
    }
    $tokens = array_values(array_filter($words, static function ($w) use ($stop) { return strlen($w) >= 2 && !in_array($w, $stop, true); }));
    $qPhon = ml_phonetic_key($rawQ);
    $qCorePhon = !empty($tokens) ? ml_phonetic_key(implode(' ', $tokens)) : $qPhon;

    $scored = [];
    $serialNames = [];
    foreach ($allMovies as $m) {
        if (!empty($m['is_serial'])) $serialNames[] = '#' . $m['code'] . ' ' . $m['name'];
        $sc = 0.0;
        $mNameN = ml_norm_text($m['name']);
        $mNameP = ml_phonetic_key($m['name']);
        $mGenN = ml_norm_text($m['genre']);
        $mCapN = ml_norm_text($m['caption']);
        $mCtrN = ml_norm_text($m['country']);
        $mYr = (string)$m['year'];
        $views = (int)$m['views'];
        $imdb = (float)str_replace(',', '.', (string)$m['imdb']);

        // 1. Kod bo'yicha aniq moslik
        if (ltrim($qNorm, '#') === (string)$m['code']) $sc += 180.0;

        // 2. Fonetik va to'liq nom mosligi ('garry poter' / 'gerry poter' -> 'Garri Potter')
        if ($qCorePhon !== '' && $mNameP !== '') {
            if ($qCorePhon === $mNameP || $qPhon === $mNameP) {
                $sc += 150.0;
            } elseif (strlen($qCorePhon) >= 4 && (strpos($mNameP, $qCorePhon) !== false || (strlen($mNameP) >= 4 && strpos($qCorePhon, $mNameP) !== false))) {
                $sc += 110.0;
            } else {
                $fullR = ml_sim_ratio($qCorePhon, $mNameP);
                if ($fullR >= 0.72) $sc += $fullR * 125.0;
            }
        }

        // 3. Har bir so'z bo'yicha fonetik + fuzzy moslik (so'z chegarasi bilan — 'gari' != 'jodugari'!)
        $mWordsP = array_values(array_filter(explode(' ', $mNameP), static function ($w) { return strlen($w) >= 2; }));
        $mWordsN = array_values(array_filter(explode(' ', $mNameN), static function ($w) { return strlen($w) >= 2; }));
        $wordHits = 0;
        foreach ($tokens as $tok) {
            $tokP = ml_phonetic_key($tok);
            $wExact = in_array($tok, $mWordsN, true) || ($tokP !== '' && in_array($tokP, $mWordsP, true));
            $wPref = false;
            if (!$wExact && strlen($tokP) >= 4) {
                foreach ($mWordsP as $mw) {
                    if (strlen($mw) >= 4 && (strpos($mw, $tokP) === 0 || strpos($tokP, $mw) === 0)) { $wPref = true; break; }
                }
            }
            if ($wExact) {
                $sc += 46.0;
                $wordHits++;
            } elseif ($wPref) {
                $sc += 36.0;
                $wordHits++;
            } elseif ($tokP !== '' && !empty($mWordsP)) {
                $bestW = 0.0;
                foreach ($mWordsP as $mw) {
                    $r = ml_sim_ratio($tokP, $mw);
                    if ($r > $bestW) $bestW = $r;
                }
                if ($bestW >= 0.75) {
                    $sc += $bestW * 46.0;
                    $wordHits++;
                }
            }
            if (strlen($tok) >= 4 && ml_contains($mCapN, $tok)) $sc += 10.0;
            if (strlen($tok) >= 4 && ml_contains($mGenN, $tok)) $sc += 14.0;
            if (strlen($tok) >= 4 && ml_contains($mCtrN, $tok)) $sc += 12.0;
        }
        if (count($tokens) >= 2 && $wordHits >= count($tokens)) {
            $sc += 45.0;
        }

        foreach ($matchedGenres as $gk) { if (ml_contains($mGenN, $gk)) $sc += 30.0; }
        if ($wantsSerial) $sc += !empty($m['is_serial']) ? 36.0 : -15.0;
        if ($targetYear !== '') {
            if ($mYr === $targetYear) $sc += 32.0;
            elseif (ctype_digit($mYr) && abs((int)$mYr - (int)$targetYear) <= 1) $sc += 12.0;
        }
        if ($wantsTop) $sc += min($views / 80.0, 22.0) + ($imdb * 2.5);
        if ($wantsNew && ctype_digit($mYr) && (int)$mYr >= 2023) $sc += 22.0;

        // Kichik tie-breaker (hech qachon tasodifiy Beethoven ni yuqoriga chiqarmaydi!)
        $sc += min($views / 3000.0, 0.8) + ($imdb * 0.08);
        $scored[] = ['score' => $sc, 'movie' => $m];
    }
    usort($scored, static function ($a, $b) { return $b['score'] <=> $a['score']; });

    $isBroadBrowse = (!empty($matchedGenres) || $wantsSerial || $wantsTop || $wantsNew || $intent !== 'movie');
    $picked = [];
    if (!empty($scored) && $scored[0]['score'] >= 90.0 && !$isBroadBrowse) {
        $topS = $scored[0]['score'];
        foreach (array_slice($scored, 0, 3) as $row) {
            if ($row['score'] >= $topS * 0.55) $picked[] = $row['movie'];
        }
    } else {
        foreach (array_slice($scored, 0, 6) as $row) {
            if ($row['score'] >= 24.0) $picked[] = $row['movie'];
        }
        if (empty($picked) && $isBroadBrowse) {
            foreach (array_slice($scored, 0, 6) as $row) $picked[] = $row['movie'];
        }
    }

    $vip7 = (int)$settingsMap['vip_7_price'];
    $vip30 = (int)$settingsMap['vip_30_price'];
    $vip90 = (int)$settingsMap['vip_90_price'];
    $dailyR = (int)$settingsMap['daily_reward_amount'];
    $refR = (int)$settingsMap['ref_reward_amount'];
    $cardI = $settingsMap['payment_card_info'];
    $freeL = $settingsMap['free_order_limit'];
    $vipL = $settingsMap['premium_order_limit'];

    // 1. Google Gemini 2.5 Flash / Pro orqali haqiqiy professional suhbat!
    $llmReply = '';
    $usedModel = '';
    $gemKey = trim((string)($settingsMap['ai_key_gemini'] ?? ''));
    if (($settingsMap['ai_enabled'] ?? '1') === '1' && $gemKey !== '' && $rawQ !== '') {
        $candTxt = '';
        foreach (array_slice($picked, 0, 10) as $cm) {
            $candTxt .= "- #{$cm['code']} {$cm['name']} ({$cm['year']}, {$cm['genre']}, IMDb {$cm['imdb']}, " . (!empty($cm['is_serial']) ? 'Serial' : 'Kino') . "): " . substr(str_replace("\n", ' ', $cm['caption']), 0, 110) . "\n";
        }
        $vipSt = $userCtx['is_vip'] ? "FAOL ({$userCtx['vip_until']} gacha, [{$userCtx['vip_tag']}])" : 'Oddiy (Standard)';
        $sysInst = "Sen «Movie Land AI» — @movieeland_bot va Movie Land WebApp ning rasmiy professional sun'iy intellekt yordamchisisiz.\n"
            . "Bot haqida to'liq ma'lumot: Kanal @movieee_land, Mavzuli Guruh @movieeland_group (Faollik, Premium Otzivlar, Buyurtmalar, Qoidalar, Muhokama), Ega: Asliddin (@asliddin_akk), WebApp: {$settingsMap['webapp_url']}.\n"
            . "Katalog: jami " . count($allMovies) . " ta kino/serial. Seriallar: " . implode(', ', array_slice($serialNames, 0, 12)) . ".\n"
            . "VIP narxlar (Bot va WebApp da bir xil): 7 kun = {$vip7} so'm, 30 kun = {$vip30} so'm, 90 kun = {$vip90} so'm. Karta: {$cardI}. Kunlik bonus: +{$dailyR} so'm, Referal: +{$refR} so'm/do'st. Buyurtma limiti: oddiy {$freeL}/kun, VIP {$vipL}/kun.\n"
            . "Foydalanuvchi: {$userCtx['name']} | Balans: {$userCtx['balance']} so'm | Takliflar: {$userCtx['refs']} | VIP: {$vipSt}.\n"
            . "Bazadagi mos kinolar (faqat shu haqiqiy #kod lardan foydalan):\n{$candTxt}\n"
            . "Qoida: Sof o'zbek tilida (ruscha yozsa rus tilida) samimiy, professional, aniq va tushunarli javob ber. Soxta kino kodi o'ylab topma. 950 belgidan oshmasin.";

        $contents = [];
        foreach (array_slice($historyIn, -8) as $h) {
            if (!is_array($h) || empty($h['text'])) continue;
            $rRole = (($h['role'] ?? '') === 'bot' || ($h['role'] ?? '') === 'model') ? 'model' : 'user';
            $contents[] = ['role' => $rRole, 'parts' => [['text' => substr((string)$h['text'], 0, 900)]]];
        }
        $contents[] = ['role' => 'user', 'parts' => [['text' => $rawQ]]];

        $gemPayload = json_encode([
            'systemInstruction' => ['parts' => [['text' => $sysInst]]],
            'contents' => $contents,
            'generationConfig' => ['temperature' => 0.68, 'maxOutputTokens' => 850],
        ], JSON_UNESCAPED_UNICODE);

        $gemModels = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite', 'gemini-2.0-flash'];
        foreach ($gemModels as $gm) {
            $gUrl = 'https://generativelanguage.googleapis.com/v1beta/models/' . $gm . ':generateContent?key=' . rawurlencode($gemKey);
            $gCtx = stream_context_create([
                'http' => [
                    'method' => 'POST',
                    'header' => "Content-Type: application/json\r\n",
                    'content' => $gemPayload,
                    'timeout' => 14,
                    'ignore_errors' => true,
                ],
            ]);
            $gRaw = @file_get_contents($gUrl, false, $gCtx);
            if ($gRaw === false) continue;
            $gData = json_decode($gRaw, true);
            if (is_array($gData) && !empty($gData['candidates'][0]['content']['parts'])) {
                $txtOut = '';
                foreach ($gData['candidates'][0]['content']['parts'] as $pt) {
                    if (empty($pt['thought']) && !empty($pt['text'])) $txtOut .= (string)$pt['text'];
                }
                if (trim($txtOut) !== '') {
                    $llmReply = trim($txtOut);
                    $usedModel = $gm;
                    break;
                }
            }
            if (is_array($gData) && isset($gData['error']['code']) && (int)$gData['error']['code'] === 403) {
                break;
            }
        }
    }

    if ($llmReply !== '') {
        // AI javobida eslatilgan #kod larni birinchi qilib qaytaramiz
        $byCode = [];
        foreach ($allMovies as $am) $byCode[$am['code']] = $am;
        $outMovies = [];
        if (preg_match_all('/#(\d{1,5})\b/', $llmReply, $cm)) {
            foreach (array_unique($cm[1]) as $mc) {
                if (isset($byCode[$mc])) $outMovies[] = $byCode[$mc];
            }
        }
        if (empty($outMovies) && $intent === 'movie') $outMovies = array_slice($picked, 0, 5);
        ml_json(['ok' => true, 'reply' => $llmReply, 'movies' => array_slice($outMovies, 0, 6), 'model' => $usedModel]);
    }

    // 2. Ichki ekspert fallback (Bot haqida ham, kinolar haqida ham to'liq aniq javob!)
    $balF = number_format($userCtx['balance'], 0, '.', ' ');
    $v7F = number_format($vip7, 0, '.', ' ');
    $v30F = number_format($vip30, 0, '.', ' ');
    $v90F = number_format($vip90, 0, '.', ' ');
    $dRF = number_format($dailyR, 0, '.', ' ');
    $rRF = number_format($refR, 0, '.', ' ');

    if ($intent === 'vip') {
        $stLine = $userCtx['is_vip']
            ? "✅ Sizda hozir VIP [{$userCtx['vip_tag']}] FAOL ({$userCtx['vip_until']} gacha)!"
            : "💰 Joriy balansingiz: {$balF} so'm.";
        $rep = "💎 Movie Land Premium (VIP) ma'lumoti:\n{$stLine}\n\n"
            . "📦 Tariflar:\n• 7 kunlik VIP: {$v7F} so'm\n• 30 kunlik VIP: {$v30F} so'm\n• 90 kunlik VIP: {$v90F} so'm\n\n"
            . "✨ Imtiyozlar: majburiy obunasiz, reklamasiz, @movieeland_group da maxsus [PREMIUM] teg va kuniga {$vipL} ta kino buyurtma!\n"
            . "💳 Profil bo'limidan balans orqali 1 bosishda yoqishingiz yoki botda karta ({$cardI}) orqali to'lashingiz mumkin.";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => [], 'model' => 'builtin-expert']);
    }
    if ($intent === 'balance') {
        $rep = "💰 Balans va Bonus tizimi ({$userCtx['name']}):\n"
            . "• Joriy balans: {$balF} so'm | Takliflar: {$userCtx['refs']} ta do'st\n"
            . "• 🎁 Kunlik bonus: har 24 soatda +{$dRF} so'm (botdagi «Bonus & Referal» da)\n"
            . "• 👥 Referal mukofoti: har bir do'stingiz uchun +{$rRF} so'm!\n\n"
            . "Profil bo'limidan shaxsiy havolangizni nusxalab do'stlarga ulashing va VIP ni bepul oling!";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => [], 'model' => 'builtin-expert']);
    }
    if ($intent === 'order') {
        $rep = "🎬 Kino buyurtma qilish:\nAgar izlagan kino bazamizda (" . count($allMovies) . " ta) topilmasa, @movieeland_bot da «🎬 Buyurtma» tugmasini bosib kino nomini yuboring. Buyurtmangiz @movieeland_group ga tushadi va adminlarimiz tez orada yuklab beradi!";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => [], 'model' => 'builtin-expert']);
    }
    if ($intent === 'howto') {
        $rep = "🧭 Movie Land dan foydalanish:\n"
            . "1) WebApp da yoki botdagi «🔍 Kino qidirish» orqali nom/kod bo'yicha toping;\n"
            . "2) Kartochkani bosib «✈️ Botda tomosha qilish» ni bosing — bot kinoni darhol yuboradi;\n"
            . "3) Premyeralar: @movieee_land | Muhokama va Buyurtmalar: @movieeland_group | Ega: @asliddin_akk.\n"
            . "Yana qanday kino izlayapsiz? Janr yoki kayfiyatingizni yozing!";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => [], 'model' => 'builtin-expert']);
    }
    if ($intent === 'greeting') {
        $rep = "Assalomu alaykum, {$userCtx['name']}! Men — Movie Land AI yordamchisiman. Sizga " . count($allMovies) . " ta kino/serial ichidan eng mosini topishda, shuningdek VIP ({$v7F} so'mdan), balans, bonuslar va bot funksiyalari bo'yicha to'liq yordam beraman!";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => array_slice($allMovies, 0, 6), 'model' => 'builtin-expert']);
    }

    if (empty($picked)) {
        $rep = "Afsuski, «{$rawQ}» bo'yicha bazamizda (" . count($allMovies) . " ta kino ichida) aniq mos kino topilmadi. Botdagi «Buyurtma» bo'limidan nomini yuboring — adminlarimiz uni tez orada yuklab berishadi! Yoki janr/kayfiyatingizni yozing, eng saralarini tanlab beraman.";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => [], 'model' => 'builtin-expert']);
    }
    if (count($picked) === 1) {
        $one = $picked[0];
        $kind = !empty($one['is_serial']) ? 'Serial' : 'Kino';
        $rep = "Albatta! Siz izlagan «{$one['name']}» ({$one['year']}) bazamizda mavjud:\n"
            . "{$kind} #{$one['code']} • IMDb {$one['imdb']}/10 • {$one['quality']}.\n"
            . "Pastdagi kartochkani bosib darhol tomosha qilishingiz mumkin!";
        ml_json(['ok' => true, 'reply' => $rep, 'movies' => [$one], 'model' => 'builtin-expert']);
    }
    $rep = "«{$rawQ}» so'rovingiz bo'yicha bazamizdan eng mos " . min(6, count($picked)) . " ta kino/serialni saralab berdim. Pastdagi kartochkani bosib darhol tomosha qiling!";
    ml_json(['ok' => true, 'reply' => $rep, 'movies' => array_slice($picked, 0, 6), 'model' => 'builtin-expert']);
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
            $rawG = (string)($r['genre'] ?: 'Jangari');
            $gParts = preg_split('/[,•|\/]+/u', $rawG);
            $gClean = [];
            if (is_array($gParts)) {
                foreach ($gParts as $gp) {
                    [, $cn] = ml_split_genre($gp);
                    if ($cn !== '' && !in_array($cn, $gClean, true)) $gClean[] = $cn;
                }
            }
            $cleanGenreStr = !empty($gClean) ? implode(', ', $gClean) : 'Jangari';
            $movies[] = [
                'code' => (string)$r['code'],
                'name' => (string)$r['name'],
                'genre' => $cleanGenreStr,
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
    // CRITICAL: /u UTF-8 modifier prevents splitting multibyte emojis into corrupt U+FFFD bytes!
    $parts = preg_split('/[,•|\/]+/u', (string)$m['genre']);
    if (!is_array($parts)) $parts = [$m['genre']];
    $seenLocal = [];
    foreach ($parts as $rawPart) {
        $rawPart = trim($rawPart);
        if ($rawPart === '') continue;
        [$icon, $cleanName] = ml_split_genre($rawPart);
        if ($cleanName === '') continue;
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
        ['flame', 'Jangari'], ['compass', 'Sarguzasht'], ['masks', 'Drama'],
        ['rocket', 'Fantastika'], ['wand', 'Fantaziya'], ['bolt', 'Triller'],
        ['shield', 'Kriminal'], ['smile', 'Komediya'], ['users', 'Oilaviy'],
        ['heart', 'Melodrama'], ['sparkles', 'Multfilm'], ['ghost', "Qo'rqinchli"],
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
