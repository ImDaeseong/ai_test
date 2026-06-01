#pragma once

#include <afx.h>
#include <afxtempl.h>
#include "GameInfoConfig.h"

enum EGameInstallType
{
    GAME_INSTALL_UNKNOWN   = 0,
    GAME_INSTALL_STEAM,
    GAME_INSTALL_EPIC,
    GAME_INSTALL_NETMARBLE
};

class CGameInstallInfo
{
public:
    CGameInstallInfo();

    EGameInstallType m_eType;
    CString m_strTypeName;
    CString m_strInstallPath;
    CString m_strExePath;
    CString m_strLauncherPath;
    CString m_strLaunchCommand;
    CString m_strVersion;
    CString m_strAppId;
    CString m_strSource;
    BOOL    m_bInstalled;
    BOOL    m_bExeExists;
};

using CGameInstallArray = CArray<CGameInstallInfo, CGameInstallInfo&>;

class CGameInstallSearchCommon
{
public:
    static CString GetInstallTypeName(EGameInstallType eType);

    static BOOL FileExists(LPCTSTR lpszPath);
    static BOOL DirectoryExists(LPCTSTR lpszPath);

    static BOOL ReadStringValue(HKEY hRoot, LPCTSTR lpszSubKey, LPCTSTR lpszValueName, CString& strValue);
    static BOOL ReadDwordValue(HKEY hRoot, LPCTSTR lpszSubKey, LPCTSTR lpszValueName, DWORD& dwValue);

    static CString NormalizePath(LPCTSTR lpszPath);
    static CString JoinPath(LPCTSTR lpszLeft, LPCTSTR lpszRight);
    static CString GetParentDirectory(LPCTSTR lpszPath);

    static CString ReadTextFile(LPCTSTR lpszPath);

    static CString ExtractJsonStringValue(const CString& strText, LPCTSTR lpszKey);
    static CString ExtractSteamAcfValue(const CString& strText, LPCTSTR lpszKey);

    static CString SearchFileOnAllDrives(LPCTSTR const* pszRelPaths);

    static CString GetExeFileVersion(LPCTSTR lpszExePath);

    static BOOL LaunchGame(const CGameInstallInfo& info, BOOL bDirect = FALSE, DWORD* pdwProcessId = NULL);

    static BOOL LaunchNetmarble(const CGameInstallInfo& info, DWORD* pdwProcessId = NULL);

private:
    static BOOL LaunchExeDirect(LPCTSTR lpszExePath, LPCTSTR lpszInstallPath, DWORD* pdwProcessId);
};
