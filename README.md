# UploadTracker

UploadZTracker ist ein Plugin für Nicotine+, das abgeschlossene Uploads in einer lokalen SQLite-Datenbank protokolliert.

Es speichert:
- Tageswerte pro Benutzer
- laufende Gesamtsummen pro Benutzer
- optional einzelne Upload-Ereignisse als Detailhistorie

## Funktionen

- erzeugt die SQLite-Datenbank beim Start automatisch, falls sie noch nicht existiert
- summiert pro Benutzer und Kalendertag
- summiert parallel als Gesamtsumme pro Benutzer
- kann zusätzlich jeden einzelnen abgeschlossenen Upload als Ereignis speichern
- kann pro Upload einen Log-Eintrag im Nicotine+-Log schreiben
- Fehler werden ins Nicotine+-Log geschrieben

## Dateien

- `__init__.py` – Plugin-Code
- `PLUGININFO` – Plugin-Metadaten
- `UploadZTracker.sqlite3` – SQLite-Datenbank, wird beim Start erzeugt

## Installation

1. Die ZIP-Datei entpacken.
2. Den Ordner `UploadZTracker` in den Nicotine+-Plugin-Ordner kopieren.
3. Das Plugin in Nicotine+ aktivieren.

## Einstellungen

Das Plugin verwendet diese Einstellungen:

### `database_filename`
Name der SQLite-Datei im Plugin-Ordner.

Standard:

```text
UploadZTracker.sqlite3
```

### `log_each_upload`
Wenn `True`, wird für jeden abgeschlossenen Upload ein normaler Log-Eintrag geschrieben.

Standard:

```text
True
```

### `store_event_rows`
Wenn `True`, wird zusätzlich zu den Summen pro Upload ein einzelner Ereignisdatensatz gespeichert.

Standard:

```text
True
```

## Datenbankschema

### Tabelle `upload_events`
Speichert einzelne abgeschlossene Uploads.

Spalten:
- `id`
- `event_ts`
- `upload_date`
- `username`
- `virtual_path`
- `real_path`
- `bytes_uploaded`

### Tabelle `daily_uploads`
Speichert aggregierte Uploads pro Benutzer und Kalendertag.

Spalten:
- `username`
- `upload_date`
- `bytes_uploaded`
- `files_uploaded`
- `updated_at`

Primärschlüssel:
- `(username, upload_date)`

### Tabelle `user_totals`
Speichert laufende Gesamtsummen pro Benutzer.

Spalten:
- `username`
- `total_bytes_uploaded`
- `total_files_uploaded`
- `first_seen_date`
- `updated_at`

## Beispielabfragen

### Tageswerte

```sql
SELECT upload_date, username, bytes_uploaded, files_uploaded
FROM daily_uploads
ORDER BY upload_date DESC, bytes_uploaded DESC;
```

### Gesamtsummen je Benutzer

```sql
SELECT username, total_bytes_uploaded, total_files_uploaded, first_seen_date, updated_at
FROM user_totals
ORDER BY total_bytes_uploaded DESC;
```

### Detailhistorie für einen Benutzer

```sql
SELECT event_ts, virtual_path, bytes_uploaded
FROM upload_events
WHERE username = 'BeispielUser'
ORDER BY event_ts DESC;
```

## Technischer Hinweis

Das Plugin verwendet den Nicotine+-Hook:

```python
upload_finished_notification(self, user, virtual_path, real_path)
```

Die Dateigröße wird beim Abschluss des Uploads über `real_path` vom lokalen Dateisystem gelesen.

## Einschränkungen

- Das Plugin sieht nur abgeschlossene Uploads.
- Wenn die Dateigröße über `real_path` nicht mehr ermittelt werden kann, wird `0` gespeichert und ein Fehler geloggt.
- Die Summen beziehen sich auf das, was beim Hook als abgeschlossen gemeldet wurde.
