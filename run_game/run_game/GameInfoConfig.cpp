#include "stdafx.h"
#include "GameInfoConfig.h"
#include "GameInstallSearchCommon.h"
#include "AppLog.h"
#include "json/json.h"

// Holds the configuration for one game loaded from GameConfig.json.
// Platform search classes use this data to decide search paths.
CGameInfo::CGameInfo()
{
    Clear();
}

// Resets all fields.
void CGameInfo::Clear()
{
    m_strGameId.Empty();
    m_bEnabled = TRUE;
    m_strGameName.Empty();
    m_strExeName.Empty();
    m_strSteamAppId.Empty();
    m_vecSteamCommonDirs.clear();
    m_strEpicManifestKeyword.Empty();
    m_strNetmarbleGameRegSubKey.Empty();
    m_strNetmarbleGameFolder.Empty();
}

static CString JsonValueToCString(const Json::Value& value)
{
    if (value.isString())
        return CString(CA2T(value.asCString()));

    if (value.isInt() || value.isUInt() || value.isInt64() || value.isUInt64())
    {
        CString strValue;
        strValue.Format(_T("%I64d"), value.asInt64());
        return strValue;
    }

    return _T("");
}

static BOOL JsonValueToBool(const Json::Value& value, BOOL bDefault)
{
    if (value.isBool())
        return value.asBool() ? TRUE : FALSE;

    if (value.isString())
    {
        CString strValue(CA2T(value.asCString()));
        strValue.Trim();
        return (strValue.CompareNoCase(_T("true")) == 0 || strValue == _T("1") || strValue.CompareNoCase(_T("yes")) == 0);
    }

    if (value.isInt() || value.isUInt())
        return (value.asInt() != 0);

    return bDefault;
}

static BOOL ApplyJsonStringValue(const Json::Value& json, LPCSTR lpszKey, CString& strValue)
{
    if (!json.isMember(lpszKey))
        return FALSE;

    CString strJsonValue = JsonValueToCString(json[lpszKey]);
    if (strJsonValue.IsEmpty())
        return FALSE;

    strValue = strJsonValue;
    return TRUE;
}

static void AddUniqueString(std::vector<CString>& vecValue, const CString& strValue)
{
    if (strValue.IsEmpty())
        return;

    for (size_t i = 0; i < vecValue.size(); ++i)
    {
        if (vecValue[i].CompareNoCase(strValue) == 0)
            return;
    }

    vecValue.push_back(strValue);
}

static void ApplyJsonSteamCommonDirs(const Json::Value& json, std::vector<CString>& vecDirs)
{
    if (!json.isMember("commonDirs") || !json["commonDirs"].isArray())
        return;

    const Json::Value& arrayValue = json["commonDirs"];
    for (Json::ArrayIndex i = 0; i < arrayValue.size(); ++i)
    {
        AddUniqueString(vecDirs, JsonValueToCString(arrayValue[i]));
    }
}

// Parses GameConfig.json text and applies the first enabled games[] entry.
BOOL CGameInfo::ApplyFromJsonText(LPCTSTR lpszJsonText)
{
    if (lpszJsonText == NULL || lpszJsonText[0] == 0)
        return FALSE;

    CT2CA strJsonA(lpszJsonText);
    Json::Reader reader;
    Json::Value root;
    if (!reader.parse((LPCSTR)strJsonA, root) || !root.isObject())
    {
        AppLog(_T("ApplyFromJsonText"), _T("JSON parse failed"));
        return FALSE;
    }

    if (!root.isMember("games") || !root["games"].isArray())
    {
        AppLog(_T("ApplyFromJsonText"), _T("Missing games array"));
        return FALSE;
    }

    const Json::Value* pGameJson = NULL;
    const Json::Value& games = root["games"];
    for (Json::ArrayIndex i = 0; i < games.size(); ++i)
    {
        if (!games[i].isObject())
            continue;

        BOOL bEnabled = TRUE;
        if (games[i].isMember("enabled"))
            bEnabled = JsonValueToBool(games[i]["enabled"], TRUE);

        if (bEnabled)
        {
            pGameJson = &games[i];
            break;
        }
    }

    if (pGameJson == NULL)
    {
        AppLog(_T("ApplyFromJsonText"), _T("No enabled game in games array"));
        return FALSE;
    }

    Clear();

    ApplyJsonStringValue(*pGameJson, "id", m_strGameId);
    if (pGameJson->isMember("enabled"))
        m_bEnabled = JsonValueToBool((*pGameJson)["enabled"], TRUE);

    ApplyJsonStringValue(*pGameJson, "gameName", m_strGameName);
    ApplyJsonStringValue(*pGameJson, "exeName", m_strExeName);

    if (pGameJson->isMember("steam") && (*pGameJson)["steam"].isObject())
    {
        const Json::Value& steam = (*pGameJson)["steam"];
        ApplyJsonStringValue(steam, "appId", m_strSteamAppId);
        ApplyJsonSteamCommonDirs(steam, m_vecSteamCommonDirs);
    }

    if (pGameJson->isMember("epic") && (*pGameJson)["epic"].isObject())
    {
        const Json::Value& epic = (*pGameJson)["epic"];
        ApplyJsonStringValue(epic, "manifestKeyword", m_strEpicManifestKeyword);
    }

    if (pGameJson->isMember("netmarble") && (*pGameJson)["netmarble"].isObject())
    {
        const Json::Value& netmarble = (*pGameJson)["netmarble"];
        ApplyJsonStringValue(netmarble, "regSubKey", m_strNetmarbleGameRegSubKey);
        ApplyJsonStringValue(netmarble, "folder", m_strNetmarbleGameFolder);
    }

    return !m_strGameName.IsEmpty() && !m_strExeName.IsEmpty();
}

static BOOL TryLocalGameInfoPath(CString& strPath, LPCTSTR lpszDirectory)
{
    if (lpszDirectory == NULL || lpszDirectory[0] == 0)
        return FALSE;

    CString strCandidate = CGameInstallSearchCommon::JoinPath(lpszDirectory, _T("GameConfig.json"));
    if (CGameInstallSearchCommon::FileExists(strCandidate))
    {
        strPath = strCandidate;
        return TRUE;
    }

    return FALSE;
}

static BOOL FindLocalGameInfoPath(CString& strPath)
{
    TCHAR szModulePath[MAX_PATH * 4] = {0};
    GetModuleFileName(NULL, szModulePath, sizeof(szModulePath) / sizeof(TCHAR));

    CString strDir = CGameInstallSearchCommon::GetParentDirectory(szModulePath);
    for (int i = 0; i < 6 && !strDir.IsEmpty(); ++i)
    {
        if (TryLocalGameInfoPath(strPath, strDir))
            return TRUE;
        strDir = CGameInstallSearchCommon::GetParentDirectory(strDir);
    }

    TCHAR szCurrentDir[MAX_PATH * 4] = {0};
    GetCurrentDirectory(sizeof(szCurrentDir) / sizeof(TCHAR), szCurrentDir);

    strDir = szCurrentDir;
    for (int j = 0; j < 6 && !strDir.IsEmpty(); ++j)
    {
        if (TryLocalGameInfoPath(strPath, strDir))
            return TRUE;
        strDir = CGameInstallSearchCommon::GetParentDirectory(strDir);
    }

    return FALSE;
}

// Searches up to 6 parent directories from the EXE and parses GameConfig.json.
BOOL CGameInfo::LoadGameInfoFromLocalFile()
{
    CString strPath;
    if (!FindLocalGameInfoPath(strPath))
    {
        AppLog(_T("LoadGameInfoFromLocalFile"), _T("GameConfig.json not found"));
        return FALSE;
    }

    CString strJson = CGameInstallSearchCommon::ReadTextFile(strPath);
    if (strJson.IsEmpty())
    {
        AppLog(_T("LoadGameInfoFromLocalFile"), _T("Read failed path=%s"), (LPCTSTR)strPath);
        return FALSE;
    }

    BOOL bResult = ApplyFromJsonText(strJson);
    AppLog(_T("LoadGameInfoFromLocalFile"), _T("path=%s result=%s game=%s exe=%s"),
        (LPCTSTR)strPath, bResult ? _T("OK") : _T("FAIL"), (LPCTSTR)m_strGameName, (LPCTSTR)m_strExeName);

    return bResult;
}

// Loads the enabled game configuration from local GameConfig.json.
BOOL CGameInfo::LoadFromLocalConfig()
{
    Clear();

    BOOL bLoaded = LoadGameInfoFromLocalFile();
    if (!bLoaded)
        AppLog(_T("LoadFromLocalConfig"), _T("GameConfig.json load failed"));

    return bLoaded;
}
