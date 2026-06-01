#pragma once

#include "GameInstallSearchCommon.h"

class CSteamLauncherSearch
{
public:
    explicit CSteamLauncherSearch(const CGameInfo& gameInfo);

    BOOL Search(CGameInstallInfo& info);

private:
    const CGameInfo& m_GameInfo;
};
