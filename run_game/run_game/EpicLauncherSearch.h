#pragma once

#include "GameInstallSearchCommon.h"

class CEpicLauncherSearch
{
public:
    explicit CEpicLauncherSearch(const CGameInfo& gameInfo);

    BOOL Search(CGameInstallInfo& info);

private:
    const CGameInfo& m_GameInfo;
};
