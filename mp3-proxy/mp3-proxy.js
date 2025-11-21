/**
 * Xiaozhi MP3 Proxy Adapter
 *
 * A Node.js Express server that acts as a proxy between Xiaozhi ESP32 devices and MP3 APIs.
 * Provides compatibility with original ESP32 code by returning relative paths instead of full URLs.
 * Features include audio caching, special stream handling for Zing MP3, and lyric proxying.
 *
 * @author Xiaozhi Team
 * @version 1.0.0
 */

const express = require('express');
const axios = require('axios');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 5005;
const MP3_API_URL = process.env.MP3_API_URL || 'http://localhost:5555';

// Audio cache to store downloaded songs in memory
// Key: songId (string), Value: Buffer containing MP3 data
const audioCache = new Map();
const CACHE_MAX_SIZE = 10;

// Known special stream key
const SPECIAL_ZING_KEY = 'zing mp3';
const SPECIAL_ZING_STREAM_PARAM = 'zing_mp3';
const ZING_RADIO = 'https://vnno-cm-3-tf-multi-playlist-zmp3.zmdcdn.me/JB2zPitWC-s/zhls/playback-realtime/audio/6ddadf76e3330a6d5322/audio.m3u8';

/**
 * Normalizes a string by converting to lowercase, removing diacritics, and trimming whitespace
 * Used for case-insensitive string matching, particularly for special stream detection
 *
 * @param {string} s - The input string to normalize
 * @returns {string} The normalized string, or empty string if input is invalid
 */
function normalizeString(s) {
    if (!s || typeof s !== 'string') return '';
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

/**
 * Handles special Zing MP3 stream using ffmpeg transcoding
 *
 * @param {object} req - Express request object
 * @param {object} res - Express response object
 */
function handleSpecialStream(req, res) {
    console.log('[PROXY_AUDIO] Serving special Zing MP3 live stream via ffmpeg transcoding');

    res.setHeader('Content-Type', 'audio/mpeg');
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');

    const ffmpegArgs = [
        '-hide_banner',
        '-loglevel', 'warning',
        '-re',
        '-i', ZING_RADIO,
        '-vn',
        '-ac', '2',
        '-ar', '44100',
        '-codec:a', 'libmp3lame',
        '-b:a', '128k',
        '-f', 'mp3',
        'pipe:1'
    ];

    const ffmpeg = spawn('ffmpeg', ffmpegArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
    let ffmpegKilled = false;

    ffmpeg.stdout.pipe(res);

    ffmpeg.stderr.on('data', (chunk) => {
        const s = String(chunk).trim();
        if (s) console.warn('[FFMPEG]', s);
    });

    ffmpeg.on('error', (err) => {
        console.error('[PROXY_AUDIO] Failed to start ffmpeg process:', err.message);
        if (!res.headersSent) res.status(500).send('ffmpeg start error');
        else res.end();
    });

    ffmpeg.on('close', (code, signal) => {
        if (!res.writableEnded) {
            try { res.end(); } catch (e) { }
        }
        if (!ffmpegKilled) {
            console.log(`[FFMPEG] Process exited with code=${code} signal=${signal}`);
        }
    });

    const cleanup = () => {
        if (!ffmpeg.killed) {
            ffmpegKilled = true;
            try { ffmpeg.kill('SIGKILL'); } catch (e) { }
        }
    };

    req.on('close', () => { cleanup(); });
    res.on('finish', () => { cleanup(); });
}

/**
 * Pre-downloads audio for a song and caches it
 *
 * @param {string} songId - The song ID to download
 */
async function preDownloadAudio(songId) {
    if (audioCache.has(songId)) return;

    console.log(`[STREAM_PCM] Pre-downloading audio for song ID: ${songId}...`);

    try {
        const streamUrl = `${MP3_API_URL}/api/song/stream?id=${songId}`;
        const audioResponse = await axios({
            method: 'GET',
            url: streamUrl,
            responseType: 'arraybuffer',
            maxRedirects: 5,
            timeout: 120000,
            headers: { 'User-Agent': 'Xiaozhi-Adapter/1.0' }
        });

        const audioBuffer = Buffer.from(audioResponse.data);
        console.log(`[STREAM_PCM] Successfully downloaded ${audioBuffer.length} bytes for song ID: ${songId}`);

        audioCache.set(songId, audioBuffer);

        // Limit cache size using LRU eviction
        if (audioCache.size > CACHE_MAX_SIZE) {
            const firstKey = audioCache.keys().next().value;
            audioCache.delete(firstKey);
            console.log(`[STREAM_PCM] Cache full, evicted song ID: ${firstKey}`);
        }
    } catch (error) {
        console.error(`[STREAM_PCM] Failed to pre-download song ID ${songId}: ${error.message}`);
    }
}

/**
 * Handler for /stream_pcm endpoint
 * Searches for songs and returns metadata with relative paths
 */
app.get('/stream_pcm', async (req, res) => {
    try {
        const { song, artist = '' } = req.query;

        if (!song) {
            return res.status(400).json({ error: 'Missing song parameter' });
        }

        console.log(`[STREAM_PCM] Searching for song: "${song}" by "${artist}"`);

        const normalized = normalizeString(song);
        if (normalized === SPECIAL_ZING_KEY || normalized === 'zing') {
            console.log('[STREAM_PCM] Special case detected: Zing MP3 live stream requested');

            const response = {
                title: 'Zing mp3 (live)',
                artist: 'ZingMp3',
                audio_url: `/proxy_audio?stream=${SPECIAL_ZING_STREAM_PARAM}`,
                lyric_url: '',
                thumbnail: '',
                duration: 0,
                language: 'vi'
            };

            console.log(`[STREAM_PCM] Returning special stream response with relative audio path: ${response.audio_url}`);
            return res.json(response);
        }

        const searchQuery = artist ? `${song} ${artist}` : song;
        const searchUrl = `${MP3_API_URL}/api/search?q=${encodeURIComponent(searchQuery)}`;

        const searchResponse = await axios.get(searchUrl, {
            timeout: 15000,
            headers: { 'User-Agent': 'Xiaozhi-Adapter/1.0' }
        });

        let songs = [];
        if (searchResponse.data.err === 0 &&
            searchResponse.data.data &&
            Array.isArray(searchResponse.data.data.songs)) {
            songs = searchResponse.data.data.songs;
        }

        if (songs.length === 0) {
            return res.status(404).json({
                error: 'Song not found',
                title: song,
                artist: artist || 'Unknown'
            });
        }

        const topSongs = songs.slice(0, 1);
        console.log(`[STREAM_PCM] Found ${topSongs.length} song(s) in search results`);

        const results = [];
        for (const songItem of topSongs) {
            const songId = songItem.encodeId;

            if (!songId) {
                console.log(`[STREAM_PCM] Skipping song without ID: ${songItem.title}`);
                continue;
            }

            console.log(`[STREAM_PCM] Processing song: "${songItem.title}" (ID: ${songId})`);

            await preDownloadAudio(songId);

            results.push({
                title: songItem.title || song,
                artist: songItem.artistsNames || artist || 'Unknown',
                audio_url: `/proxy_audio?id=${songId}`,
                lyric_url: `/proxy_lyric?id=${songId}`,
                thumbnail: songItem.thumbnail || songItem.thumbnailM || '',
                duration: songItem.duration || 0,
                language: 'unknown'
            });
        }

        if (results.length === 0) {
            return res.status(500).json({ error: 'Failed to process any songs' });
        }

        const response = results[0];

        console.log(`[STREAM_PCM] Returning song metadata with relative paths:`);
        console.log(`[STREAM_PCM]   Title: "${response.title}"`);
        console.log(`[STREAM_PCM]   Artist: "${response.artist}"`);
        console.log(`[STREAM_PCM]   Audio URL: ${response.audio_url}`);
        console.log(`[STREAM_PCM]   Lyric URL: ${response.lyric_url}`);

        res.json(response);

    } catch (error) {
        console.error(`[STREAM_PCM] Unexpected error: ${error.message}`);
        res.status(500).json({ error: 'Internal server error' });
    }
});

/**
 * Handler for /proxy_audio endpoint
 * Serves audio from cache or proxies from upstream, handles special streams
 */
app.get('/proxy_audio', async (req, res) => {
    try {
        const { id, stream } = req.query;

        if (stream && String(stream) === SPECIAL_ZING_STREAM_PARAM) {
            return handleSpecialStream(req, res);
        }

        if (!id) {
            return res.status(400).send('Missing id parameter');
        }

        console.log(`[PROXY_AUDIO] Request for song ID: ${id}`);

        if (audioCache.has(id)) {
            const audioBuffer = audioCache.get(id);
            console.log(`[PROXY_AUDIO] Serving ${audioBuffer.length} bytes from cache for song ID: ${id}`);

            res.set({
                'Content-Type': 'audio/mpeg',
                'Content-Length': audioBuffer.length,
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=86400'
            });

            return res.send(audioBuffer);
        }

        console.log(`[PROXY_AUDIO] Song ID ${id} not in cache, downloading from upstream...`);
        const streamUrl = `${MP3_API_URL}/api/song/stream?id=${id}`;

        const audioResponse = await axios({
            method: 'GET',
            url: streamUrl,
            responseType: 'arraybuffer',
            timeout: 120000
        });

        const audioBuffer = Buffer.from(audioResponse.data);
        audioCache.set(id, audioBuffer);
        console.log(`[PROXY_AUDIO] Downloaded and cached ${audioBuffer.length} bytes for song ID: ${id}`);

        res.set({
            'Content-Type': 'audio/mpeg',
            'Content-Length': audioBuffer.length,
            'Accept-Ranges': 'bytes'
        });

        res.send(audioBuffer);

    } catch (error) {
        console.error(`[PROXY_AUDIO] Error serving audio: ${error.message}`);
        res.status(500).send('Failed to proxy audio');
    }
});

/**
 * Handler for /proxy_lyric endpoint
 * Proxies lyrics from upstream API
 */
app.get('/proxy_lyric', async (req, res) => {
    try {
        const { id } = req.query;
        if (!id) {
            return res.status(400).send('Missing id parameter');
        }

        console.log(`[PROXY_LYRIC] Request for lyrics of song ID: ${id}`);

        const lyricUrl = `${MP3_API_URL}/api/lyric?id=${id}`;
        const response = await axios.get(lyricUrl, { timeout: 10000 });

        if (response.data && response.data.err === 0 && response.data.data) {
            const lyricData = response.data.data;

            if (lyricData.file) {
                console.log(`[PROXY_LYRIC] Serving lyrics from file URL for song ID: ${id}`);
                const lyricContent = await axios.get(lyricData.file);
                res.set('Content-Type', 'text/plain; charset=utf-8');
                return res.send(lyricContent.data);
            }

            if (Array.isArray(lyricData.sentences)) {
                console.log(`[PROXY_LYRIC] Converting sentence data to LRC format for song ID: ${id}`);
                let lrcContent = '';
                lyricData.sentences.forEach(s => {
                    const words = s.words || [];
                    words.forEach(w => {
                        const time = w.startTime || 0;
                        const minutes = Math.floor(time / 60000);
                        const seconds = Math.floor((time % 60000) / 1000);
                        const ms = Math.floor((time % 1000) / 10);
                        lrcContent += `[${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(ms).padStart(2, '0')}]${w.data}\n`;
                    });
                });
                res.set('Content-Type', 'text/plain; charset=utf-8');
                return res.send(lrcContent);
            }

            console.log(`[PROXY_LYRIC] No lyrics available for song ID: ${id}`);
            return res.status(404).send('Lyric not found');
        }

        console.log(`[PROXY_LYRIC] Upstream API returned no lyrics for song ID: ${id}`);
        res.status(404).send('Lyric not found');

    } catch (error) {
        console.error(`[PROXY_LYRIC] Error retrieving lyrics for song ID ${id}: ${error.message}`);
        res.status(404).send('Lyric not found');
    }
});

/**
 * Handler for /health endpoint
 * Returns server health status and cache information
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        cache_size: audioCache.size,
        cached_songs: Array.from(audioCache.keys())
    });
});

app.listen(PORT, () => {
    console.log('='.repeat(80));
    console.log('Xiaozhi MP3 Proxy Adapter Server Started');
    console.log('='.repeat(80));
    console.log(`Server listening on port: ${PORT}`);
    console.log(`Upstream MP3 API endpoint: ${MP3_API_URL}`);
    console.log(`Audio cache enabled (max ${CACHE_MAX_SIZE} songs in memory)`);
    console.log(`Response format: RELATIVE PATHS (ESP32 auto-appends base URL)`);
    console.log('');
    console.log('Available endpoints:');
    console.log(`   GET /stream_pcm?song=<name>&artist=<name> - Search and stream songs`);
    console.log(`   GET /proxy_audio?id=<songId> - Get cached audio file`);
    console.log(`   GET /proxy_audio?stream=zing_mp3 - Get Zing MP3 live stream`);
    console.log(`   GET /proxy_lyric?id=<songId> - Get song lyrics`);
    console.log(`   GET /health - Server health check`);
    console.log('');
    console.log('Special features:');
    console.log('   • Request "/stream_pcm?song=zing mp3" for live Zing MP3 radio');
    console.log('   • Automatic audio caching with LRU eviction');
    console.log('   • Real-time M3U8 to MP3 transcoding for live streams');
    console.log('='.repeat(80));
});
