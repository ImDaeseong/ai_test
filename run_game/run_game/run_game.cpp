#include "stdafx.h"
#include "run_game.h"
#include "run_gameDlg.h"
#include "GameInstallInfoManager.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

BEGIN_MESSAGE_MAP(Crun_gameApp, CWinAppEx)
END_MESSAGE_MAP()

Crun_gameApp::Crun_gameApp()
{
}

Crun_gameApp theApp;

BOOL Crun_gameApp::InitInstance()
{
	INITCOMMONCONTROLSEX InitCtrls;
	InitCtrls.dwSize = sizeof(InitCtrls);
	InitCtrls.dwICC = ICC_WIN95_CLASSES;
	InitCommonControlsEx(&InitCtrls);

	CWinAppEx::InitInstance();

	AfxEnableControlContainer();

	// Startup order:
	// 1. Create the manager.
	// 2. Prepare the active CGameInfo defaults.
	// 3. Search install paths from the dialog.
	CGameInstallInfoManager::GetInstance();

	Crun_gameDlg dlg;
	m_pMainWnd = &dlg;
	INT_PTR nResponse = dlg.DoModal();
	if (nResponse == IDOK)
	{
	}
	else if (nResponse == IDCANCEL)
	{
	}

	return FALSE;
}

