#pragma once

#include "GameInstallSearch.h"
#include <afxmt.h>

class Crun_gameDlg;

class CGameInstallInfoManager
{
public:
    static CGameInstallInfoManager* GetInstance();
    static void ReleaseInstance();

    void SetParent(Crun_gameDlg* pParent);
    BOOL SearchInstallPrograms();
    void ClearInstallInfo();

    int GetInstallInfoCount();
    BOOL GetInstallInfo(int nIndex, CGameInstallInfo& info);

    CString GetExeVersion(const CString& strExePath);
    BOOL RunGameByIndex(int nIndex, BOOL bDirect, DWORD* pdwProcessId = NULL);
    BOOL RunGame(const CGameInstallInfo& info, BOOL bDirect, DWORD* pdwProcessId = NULL);

private:
    CGameInstallInfoManager();
    virtual ~CGameInstallInfoManager();

    static CGameInstallInfoManager* m_pInstance;
    static CCriticalSection         m_InstanceLock;

    Crun_gameDlg*      m_pParent;
    CGameInstallSearch m_Search;
    CGameInstallArray  m_arrInstallInfo;
};
