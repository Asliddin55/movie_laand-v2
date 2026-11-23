<?php
/**
 * Movie Land Ultra — MyXvest Native WebApp Entry Point
 * Serves webapp/index.html directly from https://6b02fedeb2d06.myxvest1.ru/
 */
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-cache, must-revalidate');
$htmlFile = __DIR__ . '/webapp/index.html';
if (is_file($htmlFile)) {
    readfile($htmlFile);
    exit;
}
http_response_code(503);
echo '<!doctype html><meta charset="utf-8"><body style="background:#0b0c10;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh"><h2>Movie Land WebApp yuklanmoqda...</h2></body>';
