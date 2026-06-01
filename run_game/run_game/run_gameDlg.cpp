#include "stdafx.h"
#include "run_game.h"
#include "run_gameDlg.h"
#include "AppLog.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

Crun_gameDlg::Crun_gameDlg(CWnd* pParent /*=NULL*/)
	: CDialog(Crun_gameDlg::IDD, pParent)
{
}

void Crun_gameDlg::DoDataExchange(CDataExchange* pDX)
{
	CDialog::DoDataExchange(pDX);
}

BEGIN_MESSAGE_MAP(Crun_gameDlg, CDialog)
	ON_WM_PAINT()
	ON_WM_DESTROY()
	ON_BN_CLICKED(IDC_BUTTON1, &Crun_gameDlg::OnBnClickedButton1)
	ON_BN_CLICKED(IDC_BUTTON2, &Crun_gameDlg::OnBnClickedButton2)
	ON_BN_CLICKED(IDC_BUTTON3, &Crun_gameDlg::OnBnClickedButton3)
END_MESSAGE_MAP()

BOOL Crun_gameDlg::OnInitDialog()
{
	CDialog::OnInitDialog();

	CGameInstallInfoManager* pMgr = CGameInstallInfoManager::GetInstance();
	pMgr->SetParent(this);
	pMgr->SearchInstallPrograms();

	int nInstallCount = pMgr->GetInstallInfoCount();

	AppLog(_T("OnInitDialog"), _T("=== Game install search result: %d ==="), nInstallCount);

	for (int i = 0; i < nInstallCount; ++i)
	{
		CGameInstallInfo info;
		if (!pMgr->GetInstallInfo(i, info))
			continue;

		CString strExeVer = pMgr->GetExeVersion(info.m_strExePath);
		CString strDisplayVer = strExeVer.IsEmpty() ? info.m_strVersion : strExeVer;
		if (strDisplayVer.IsEmpty())
			strDisplayVer = _T("Unknown");

		AppLog(_T("OnInitDialog"), _T("[%d] platform : %s"), i + 1, (LPCTSTR)info.m_strTypeName);
		AppLog(_T("OnInitDialog"), _T("    install  : %s"), (LPCTSTR)info.m_strInstallPath);
		AppLog(_T("OnInitDialog"), _T("    exe      : %s"), (LPCTSTR)info.m_strExePath);
		AppLog(_T("OnInitDialog"), _T("    launcher : %s"), (LPCTSTR)info.m_strLauncherPath);
		AppLog(_T("OnInitDialog"), _T("    command  : %s"), (LPCTSTR)info.m_strLaunchCommand);
		AppLog(_T("OnInitDialog"), _T("    app id   : %s"), (LPCTSTR)info.m_strAppId);
		AppLog(_T("OnInitDialog"), _T("    version  : %s"), (LPCTSTR)strDisplayVer);
		AppLog(_T("OnInitDialog"), _T("    installed: %s"), info.m_bInstalled ? _T("YES") : _T("NO"));
		AppLog(_T("OnInitDialog"), _T("    exe exist: %s"), info.m_bExeExists ? _T("YES") : _T("NO"));
	}

	return TRUE;
}

void Crun_gameDlg::OnPaint()
{
	CPaintDC dc(this);
}

void Crun_gameDlg::OnDestroy()
{
	CDialog::OnDestroy();
	CGameInstallInfoManager::ReleaseInstance();
	CAppLog::ReleaseInstance();
}

void Crun_gameDlg::OnBnClickedButton1()
{
	LaunchByType(GAME_INSTALL_STEAM);
}

void Crun_gameDlg::OnBnClickedButton2()
{
	LaunchByType(GAME_INSTALL_NETMARBLE);
}

void Crun_gameDlg::OnBnClickedButton3()
{
	LaunchByType(GAME_INSTALL_EPIC);
}

void Crun_gameDlg::LaunchByType(EGameInstallType eType)
{
	CGameInstallInfoManager* pMgr = CGameInstallInfoManager::GetInstance();

	int nCount = pMgr->GetInstallInfoCount();
	for (int i = 0; i < nCount; ++i)
	{
		CGameInstallInfo info;		
		if (!pMgr->GetInstallInfo(i, info))
			continue;

		if (info.m_eType != eType)
			continue;

		DWORD dwPid = 0;
		BOOL bLaunched = pMgr->RunGameByIndex(i, FALSE, &dwPid);

		AppLog(_T("LaunchByType"), _T("platform=%s result=%s pid=%u"),(LPCTSTR)info.m_strTypeName, bLaunched ? _T("OK") : _T("FAIL"), dwPid);
		return;
	}

	// 탐지된 항목 없음
	CString strMsg;
	strMsg.Format(_T("%s 설치를 찾을 수 없습니다."),(LPCTSTR)CGameInstallSearchCommon::GetInstallTypeName(eType));
	AfxMessageBox(strMsg, MB_OK | MB_ICONWARNING);
}
