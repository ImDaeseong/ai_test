#include "stdafx.h"
#include "SteamLauncherSearch.h"
#include "AppLog.h"

// Steam 플랫폼에서 게임 설치 정보를 탐지한다.
// 탐지 순서: 레지스트리(SteamExe) → 드라이브 전수 탐색 → ACF 매니페스트 파싱
// gameInfo: 탐지 대상 게임 설정 정보 (참조로 보관, 호출자의 수명과 동일해야 한다)
CSteamLauncherSearch::CSteamLauncherSearch(const CGameInfo& gameInfo) : m_GameInfo(gameInfo)
{
}

// Steam 설치 정보를 수집하여 info를 채운다.
// m_bInstalled(레지스트리 Installed=1) 또는 m_bExeExists 중 하나라도 TRUE면 TRUE를 반환한다.
BOOL CSteamLauncherSearch::Search(CGameInstallInfo& info)
{
    CString strSteamExe;
    CString strAppKey;
    DWORD dwInstalled = 0;

    strAppKey.Format(_T("SOFTWARE\\Valve\\Steam\\Apps\\%s"), (LPCTSTR)m_GameInfo.m_strSteamAppId);

    if (!CGameInstallSearchCommon::ReadStringValue(HKEY_CURRENT_USER, _T("SOFTWARE\\Valve\\Steam"), _T("SteamExe"), strSteamExe))
    {
        static LPCTSTR s_pszSteamRel[] = {
            _T("Program Files (x86)\\Steam\\steam.exe"),
            _T("Program Files\\Steam\\steam.exe"),
            _T("Steam\\steam.exe"),
            NULL
        };

        strSteamExe = CGameInstallSearchCommon::SearchFileOnAllDrives(s_pszSteamRel);
        if (strSteamExe.IsEmpty())
            return FALSE;
    }

    CGameInstallSearchCommon::ReadDwordValue(HKEY_CURRENT_USER, strAppKey, _T("Installed"), dwInstalled);

    CString strSteamRoot = CGameInstallSearchCommon::GetParentDirectory(strSteamExe);
    CString strSteamCommonRoot = CGameInstallSearchCommon::JoinPath(strSteamRoot, _T("steamapps\\common"));
    CString strInstallPath;
    CString strExePath;

    for (size_t i = 0; i < m_GameInfo.m_vecSteamCommonDirs.size(); ++i)
    {
        strInstallPath = CGameInstallSearchCommon::JoinPath(strSteamCommonRoot, m_GameInfo.m_vecSteamCommonDirs[i]);
        strExePath = CGameInstallSearchCommon::JoinPath(strInstallPath, m_GameInfo.m_strExeName);
        if (CGameInstallSearchCommon::FileExists(strExePath))
            break;
    }

    CString strManifestPath;
    strManifestPath.Format(_T("steamapps\\appmanifest_%s.acf"), (LPCTSTR)m_GameInfo.m_strSteamAppId);
    strManifestPath = CGameInstallSearchCommon::JoinPath(strSteamRoot, strManifestPath);

    CString strAcf = CGameInstallSearchCommon::ReadTextFile(strManifestPath);
    CString strInstallDir = CGameInstallSearchCommon::ExtractSteamAcfValue(strAcf, _T("installdir"));

    if (!strInstallDir.IsEmpty())
    {
        CString strByManifest = CGameInstallSearchCommon::JoinPath(strSteamCommonRoot, strInstallDir);
        CString strByManifestExe = CGameInstallSearchCommon::JoinPath(strByManifest, m_GameInfo.m_strExeName);

        if (CGameInstallSearchCommon::FileExists(strByManifestExe))
        {
            strInstallPath = strByManifest;
            strExePath = strByManifestExe;
        }
    }

    CString strBuildId = CGameInstallSearchCommon::ExtractSteamAcfValue(strAcf, _T("buildid"));

    info.m_eType = GAME_INSTALL_STEAM;
    info.m_strTypeName = CGameInstallSearchCommon::GetInstallTypeName(info.m_eType);
    info.m_strInstallPath = CGameInstallSearchCommon::NormalizePath(strInstallPath);
    info.m_strExePath = CGameInstallSearchCommon::NormalizePath(strExePath);
    info.m_strLauncherPath = CGameInstallSearchCommon::NormalizePath(strSteamExe);
    info.m_strLaunchCommand.Format(_T("steam://rungameid/%s"), (LPCTSTR)m_GameInfo.m_strSteamAppId);
    info.m_strAppId = m_GameInfo.m_strSteamAppId;
    info.m_strVersion = strBuildId;
    info.m_strSource = _T("HKCU\\SOFTWARE\\Valve\\Steam, Steam appmanifest");
    info.m_bInstalled = (dwInstalled == 1);
    info.m_bExeExists = CGameInstallSearchCommon::FileExists(info.m_strExePath);

    BOOL bResult = info.m_bInstalled || info.m_bExeExists;
    
	AppLog(_T("CSteamLauncherSearch::Search"), _T("result=%s installed=%s exeExists=%s"), bResult ? _T("FOUND") : _T("NOT FOUND"), info.m_bInstalled ? _T("YES") : _T("NO"), info.m_bExeExists ? _T("YES") : _T("NO"));
    AppLog(_T("CSteamLauncherSearch::Search"), _T("launcher=%s"), (LPCTSTR)info.m_strLauncherPath);
    AppLog(_T("CSteamLauncherSearch::Search"), _T("install =%s"), (LPCTSTR)info.m_strInstallPath);
    AppLog(_T("CSteamLauncherSearch::Search"), _T("exe     =%s"), (LPCTSTR)info.m_strExePath);
    AppLog(_T("CSteamLauncherSearch::Search"), _T("command =%s"), (LPCTSTR)info.m_strLaunchCommand);
    AppLog(_T("CSteamLauncherSearch::Search"), _T("version =%s"), (LPCTSTR)info.m_strVersion);

    return bResult;
}
