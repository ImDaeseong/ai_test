#pragma once

#include <afx.h>
#include <vector>

class CGameInfo
{
public:
    CGameInfo();

    CString m_strGameId;
    BOOL    m_bEnabled;
    CString m_strGameName;
    CString m_strExeName;
    CString m_strSteamAppId;
    std::vector<CString> m_vecSteamCommonDirs;
    CString m_strEpicManifestKeyword;
    CString m_strNetmarbleGameRegSubKey;
    CString m_strNetmarbleGameFolder;

    void Clear();

    BOOL LoadFromLocalConfig();
    BOOL LoadGameInfoFromLocalFile();
    BOOL ApplyFromJsonText(LPCTSTR lpszJsonText);
};
