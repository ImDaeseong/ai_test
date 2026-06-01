#pragma once

#include "GameInstallInfoManager.h"

class Crun_gameDlg : public CDialog
{
public:
	Crun_gameDlg(CWnd* pParent = NULL);	// standard constructor

	enum { IDD = IDD_RUN_GAME_DIALOG };

	protected:
	virtual void DoDataExchange(CDataExchange* pDX);	// DDX/DDV support

protected:
	virtual BOOL OnInitDialog();
	afx_msg void OnPaint();
	afx_msg void OnDestroy();
	DECLARE_MESSAGE_MAP()

public:
	afx_msg void OnBnClickedButton1();
	afx_msg void OnBnClickedButton2();
	afx_msg void OnBnClickedButton3();

private:
	void LaunchByType(EGameInstallType eType);
};
