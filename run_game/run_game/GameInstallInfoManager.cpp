#include "stdafx.h"
#include "GameInstallInfoManager.h"

CGameInstallInfoManager* CGameInstallInfoManager::m_pInstance = NULL;
CCriticalSection         CGameInstallInfoManager::m_InstanceLock;

CGameInstallInfoManager* CGameInstallInfoManager::GetInstance()
{
    CSingleLock lock(&m_InstanceLock, TRUE);
    if (m_pInstance == NULL)
        m_pInstance = new CGameInstallInfoManager();
    return m_pInstance;
}

void CGameInstallInfoManager::ReleaseInstance()
{
    CSingleLock lock(&m_InstanceLock, TRUE);
    if (m_pInstance != NULL)
    {
        delete m_pInstance;
        m_pInstance = NULL;
    }
}

CGameInstallInfoManager::CGameInstallInfoManager()
{
    m_pParent = NULL;
}

CGameInstallInfoManager::~CGameInstallInfoManager()
{
    ClearInstallInfo();
}

void CGameInstallInfoManager::SetParent(Crun_gameDlg* pParent)
{
    m_pParent = pParent;
}

BOOL CGameInstallInfoManager::SearchInstallPrograms()
{
    ClearInstallInfo();
    m_Search.SearchAll(m_arrInstallInfo);
    return (m_arrInstallInfo.GetSize() > 0);
}

void CGameInstallInfoManager::ClearInstallInfo()
{
    m_arrInstallInfo.RemoveAll();
}

int CGameInstallInfoManager::GetInstallInfoCount()
{
    return (int)m_arrInstallInfo.GetSize();
}

BOOL CGameInstallInfoManager::GetInstallInfo(int nIndex, CGameInstallInfo& info)
{
    if (nIndex < 0 || nIndex >= m_arrInstallInfo.GetSize())
        return FALSE;

    info = m_arrInstallInfo.GetAt(nIndex);
    return TRUE;
}

CString CGameInstallInfoManager::GetExeVersion(const CString& strExePath)
{
    return CGameInstallSearchCommon::GetExeFileVersion(strExePath);
}

BOOL CGameInstallInfoManager::RunGameByIndex(int nIndex, BOOL bDirect, DWORD* pdwProcessId)
{
    CGameInstallInfo info;
    if (!GetInstallInfo(nIndex, info))
        return FALSE;

    return RunGame(info, bDirect, pdwProcessId);
}

BOOL CGameInstallInfoManager::RunGame(const CGameInstallInfo& info, BOOL bDirect, DWORD* pdwProcessId)
{
    return CGameInstallSearchCommon::LaunchGame(info, bDirect, pdwProcessId);
}
