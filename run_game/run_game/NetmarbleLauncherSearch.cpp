#include "stdafx.h"
#include "NetmarbleLauncherSearch.h"
#include "AppLog.h"

// Netmarble 플랫폼에서 게임 설치 정보를 탐지한다.
// 탐지 순서: 레지스트리(AppDrive·path) → 드라이브 전수 탐색
// gameInfo: 탐지 대상 게임 설정 정보 (참조로 보관, 호출자의 수명과 동일해야 한다)
CNetmarbleLauncherSearch::CNetmarbleLauncherSearch(const CGameInfo& gameInfo) : m_GameInfo(gameInfo)
{
}

// Netmarble 설치 정보를 수집하여 info를 채운다.
// m_bExeExists 또는 런처 파일 존재 중 하나라도 TRUE면 TRUE를 반환한다.
BOOL CNetmarbleLauncherSearch::Search(CGameInstallInfo& info)
{
    CString strLauncherRoot;
    CString strInstallPath;
    CString strLauncherPath;
    CString strExePath;

    CGameInstallSearchCommon::ReadStringValue(HKEY_CURRENT_USER, _T("SOFTWARE\\Netmarble Corp"), _T("AppDrive"), strLauncherRoot);
    CGameInstallSearchCommon::ReadStringValue(HKEY_CURRENT_USER, m_GameInfo.m_strNetmarbleGameRegSubKey, _T("path"), strInstallPath);

    if (!strLauncherRoot.IsEmpty())
        strLauncherPath = CGameInstallSearchCommon::JoinPath(strLauncherRoot, _T("Netmarble Launcher.exe"));

    if (!strInstallPath.IsEmpty())
        strExePath = CGameInstallSearchCommon::JoinPath(strInstallPath, m_GameInfo.m_strExeName);

    if (!CGameInstallSearchCommon::FileExists(strLauncherPath))
    {
        static LPCTSTR s_pszNMLaunchRel[] = {
            _T("Program Files (x86)\\Netmarble\\Netmarble Launcher\\Netmarble Launcher.exe"),
            _T("Program Files\\Netmarble\\Netmarble Launcher\\Netmarble Launcher.exe"),
            _T("Netmarble\\Netmarble Launcher\\Netmarble Launcher.exe"),
            NULL
        };
        strLauncherPath = CGameInstallSearchCommon::SearchFileOnAllDrives(s_pszNMLaunchRel);
    }

    if (!CGameInstallSearchCommon::FileExists(strExePath))
    {
        CString strRel0 = CGameInstallSearchCommon::JoinPath(CGameInstallSearchCommon::JoinPath(_T("Program Files (x86)\\Netmarble\\Netmarble Game"), m_GameInfo.m_strNetmarbleGameFolder), m_GameInfo.m_strExeName);
        
		CString strRel1 = CGameInstallSearchCommon::JoinPath(CGameInstallSearchCommon::JoinPath(_T("Program Files\\Netmarble\\Netmarble Game"), m_GameInfo.m_strNetmarbleGameFolder), m_GameInfo.m_strExeName);
        
		CString strRel2 = CGameInstallSearchCommon::JoinPath(CGameInstallSearchCommon::JoinPath(_T("Netmarble"), m_GameInfo.m_strNetmarbleGameFolder), m_GameInfo.m_strExeName);
        
		CString strRel3 = CGameInstallSearchCommon::JoinPath(CGameInstallSearchCommon::JoinPath(_T("Netmarble\\Netmarble Game"), m_GameInfo.m_strNetmarbleGameFolder), m_GameInfo.m_strExeName);

        LPCTSTR pszNMGameRel[] = {strRel0, strRel1, strRel2, strRel3, NULL};

        CString strFoundExe = CGameInstallSearchCommon::SearchFileOnAllDrives(pszNMGameRel);
        if (!strFoundExe.IsEmpty())
        {
            strInstallPath = CGameInstallSearchCommon::GetParentDirectory(strFoundExe);
            strExePath = strFoundExe;
        }
    }

    info.m_eType = GAME_INSTALL_NETMARBLE;
    info.m_strTypeName = CGameInstallSearchCommon::GetInstallTypeName(info.m_eType);
    info.m_strInstallPath = CGameInstallSearchCommon::NormalizePath(strInstallPath);
    info.m_strExePath = CGameInstallSearchCommon::NormalizePath(strExePath);
    info.m_strLauncherPath = CGameInstallSearchCommon::NormalizePath(strLauncherPath);
    info.m_strLaunchCommand = _T("");
    info.m_strSource = _T("HKCU\\SOFTWARE\\Netmarble Corp, Netmarble game registry");
    info.m_bInstalled = CGameInstallSearchCommon::DirectoryExists(info.m_strInstallPath);
    info.m_bExeExists = CGameInstallSearchCommon::FileExists(info.m_strExePath);

    BOOL bResult = info.m_bExeExists || CGameInstallSearchCommon::FileExists(info.m_strLauncherPath);
    
	AppLog(_T("CNetmarbleLauncherSearch::Search"), _T("result=%s installed=%s exeExists=%s"), bResult ? _T("FOUND") : _T("NOT FOUND"), info.m_bInstalled ? _T("YES") : _T("NO"), info.m_bExeExists ? _T("YES") : _T("NO"));
    AppLog(_T("CNetmarbleLauncherSearch::Search"), _T("launcher=%s"), (LPCTSTR)info.m_strLauncherPath);
    AppLog(_T("CNetmarbleLauncherSearch::Search"), _T("install =%s"), (LPCTSTR)info.m_strInstallPath);
    AppLog(_T("CNetmarbleLauncherSearch::Search"), _T("exe     =%s"), (LPCTSTR)info.m_strExePath);

    return bResult;
}

