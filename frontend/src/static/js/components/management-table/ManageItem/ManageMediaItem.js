import React, { useRef, useState, useEffect, useCallback } from 'react';
import { usePopup } from '../../../utils/hooks/usePopup';
import { formatManagementTableDate, translateString } from '../../../utils/helpers/';
import { PageStore } from '../../../utils/stores/';
import { PopupMain } from '../../_shared';
import { MaterialIcon } from '../../_shared/material-icon/MaterialIcon';

function ManageItemTitle(props) {
    if (void 0 !== props.title && void 0 !== props.url) {
        return (
            <a href={props.url} title={props.title}>
                {props.title}
            </a>
        );
    }

    if (void 0 !== props.title) {
        return props.title;
    }

    if (void 0 !== props.url) {
        return props.url;
    }

    return <i className="non-available">N/A</i>;
}

export function ManageItemDate(props) {
    if (void 0 !== props.date) {
        return formatManagementTableDate(new Date(Date.parse(props.date)));
    }

    return <i className="non-available">N/A</i>;
}

function ManageItemMediaAuthor(props) {
    if (void 0 !== props.name && void 0 !== props.url) {
        return (
            <a href={props.url} title={props.name}>
                {props.name}
            </a>
        );
    }

    if (void 0 !== props.name) {
        return props.name;
    }

    if (void 0 !== props.url) {
        return props.url;
    }

    return <i className="non-available">N/A</i>;
}

function ManageItemMediaActions(props) {
    const [popupContentRef, PopupContent, PopupTrigger] = usePopup();
    const [isOpenPopup, setIsOpenPopup] = useState(false);

    const [migrateRef, MigrateContent, MigrateTrigger] = usePopup();
    const [pathState, setPathState] = useState({ loading: false, eligible: null, already: false, reason: '' });

    function onPopupShow() {
        setIsOpenPopup(true);
    }

    function onMigrateShow() {
        setIsOpenPopup(true);

        if ('function' !== typeof props.onCheckMigratePaths) {
            return;
        }

        setPathState({ loading: true, eligible: null, already: false, reason: '' });
        props
            .onCheckMigratePaths(props.token)
            .then((data) =>
                setPathState({
                    loading: false,
                    eligible: true === data.eligible,
                    already: true === data.already_migrated,
                    reason: data.reason || '',
                })
            )
            .catch(() =>
                setPathState({
                    loading: false,
                    eligible: false,
                    already: false,
                    reason: translateString('Could not check this media.'),
                })
            );
    }

    function onMigrateCancel() {
        migrateRef.current.tryToHide();
    }

    function onMigrateProceed() {
        migrateRef.current.tryToHide();
        if ('function' === typeof props.onMigratePaths) {
            // the list reports the outcome itself; a failure has nothing more to do here
            props.onMigratePaths(props.token).catch(() => {});
        }
    }

    function onPopupHide() {
        setIsOpenPopup(false);
    }

    function onCancel() {
        popupContentRef.current.tryToHide();
        if ('function' === typeof props.onCancel) {
            props.onCancel();
        }
    }

    function onProceed() {
        popupContentRef.current.tryToHide();
        if ('function' === typeof props.onProceed) {
            props.onProceed();
        }
    }

    const positionState = { updating: false, pending: 0 };

    const onWindowResize = useCallback(function () {
        if (positionState.updating) {
            positionState.pending = positionState.pending + 1;
        } else {
            positionState.updating = true;

            const popupElem = props.containerRef.current.querySelector('.popup');

            if (popupElem) {
                const containerClientRect = props.containerRef.current.getBoundingClientRect();

                popupElem.style.position = 'fixed';
                popupElem.style.left = containerClientRect.x + 'px';

                if (
                    document.body.offsetHeight <
                    32 + popupElem.offsetHeight + window.scrollY + containerClientRect.top
                ) {
                    popupElem.style.top = containerClientRect.y - popupElem.offsetHeight + 'px';
                } else {
                    popupElem.style.top = containerClientRect.y + containerClientRect.height + 'px';
                }
            }

            setTimeout(() => {
                positionState.updating = false;

                if (positionState.pending) {
                    positionState.pending = 0;
                    onWindowResize();
                }
            }, 8);
        }
    }, []);

    useEffect(() => {
        if (isOpenPopup) {
            PageStore.on('window_scroll', onWindowResize);
            PageStore.on('window_resize', onWindowResize);
            onWindowResize();
        } else {
            PageStore.removeListener('window_scroll', onWindowResize);
            PageStore.removeListener('window_resize', onWindowResize);
        }
    }, [isOpenPopup]);

    return (
        <div ref={props.containerRef} className="actions">
            <PopupTrigger contentRef={popupContentRef}>
                <button title={'Delete' + (void 0 !== props.title ? ' "' + props.title + '"' : '')}>Delete</button>
            </PopupTrigger>

            {'function' === typeof props.onMigratePaths ? (
                <>
                    <span className="seperator">|</span>
                    <MigrateTrigger contentRef={migrateRef}>
                        <button
                            className="mi-migrate-paths"
                            title={
                                translateString('Migrate paths') +
                                (void 0 !== props.title ? ' "' + props.title + '"' : '')
                            }
                        >
                            {translateString('Migrate paths')}
                        </button>
                    </MigrateTrigger>

                    <MigrateContent contentRef={migrateRef} showCallback={onMigrateShow} hideCallback={onPopupHide}>
                        <PopupMain>
                            <div className="popup-message">
                                <span className="popup-message-title">{translateString('Path migration')}</span>
                                <span className="popup-message-main">
                                    {pathState.loading
                                        ? translateString('Checking') + '\u2026'
                                        : pathState.already
                                          ? translateString('This media is already on the sharded layout.')
                                          : false === pathState.eligible
                                            ? translateString('Cannot migrate now:') + ' ' + pathState.reason
                                            : translateString(
                                                  'Move the files of this media to the sharded layout? They are copied and verified first, and the old files are deleted only after every check passes.'
                                              )}
                                </span>
                            </div>
                            <hr />
                            <span className="popup-message-bottom">
                                <button className="button-link cancel-profile-removal" onClick={onMigrateCancel}>
                                    CANCEL
                                </button>
                                {pathState.loading || pathState.already || false === pathState.eligible ? null : (
                                    <button
                                        className="button-link proceed-profile-removal proceed-path-migration"
                                        onClick={onMigrateProceed}
                                    >
                                        PROCEED
                                    </button>
                                )}
                            </span>
                        </PopupMain>
                    </MigrateContent>
                </>
            ) : null}

            <PopupContent contentRef={popupContentRef} showCallback={onPopupShow} hideCallback={onPopupHide}>
                <PopupMain>
                    <div className="popup-message">
                        <span className="popup-message-title">Media removal</span>
                        <span className="popup-message-main">
                            {"You're willing to remove media" +
                                (void 0 !== props.title ? ' "' + props.title + '"' : '')}
                            ?
                        </span>
                    </div>
                    <hr />
                    <span className="popup-message-bottom">
                        <button className="button-link cancel-profile-removal" onClick={onCancel}>
                            CANCEL
                        </button>
                        <button className="button-link proceed-profile-removal" onClick={onProceed}>
                            PROCEED
                        </button>
                    </span>
                </PopupMain>
            </PopupContent>
        </div>
    );
}

export function ManageMediaItem(props) {
    const actionsContainerRef = useRef(null);

    const [selected, setSelected] = useState(false);

    function onRowCheck() {
        setSelected(!selected);
    }

    function onClickProceed() {
        if ('function' === typeof props.onProceedRemoval) {
            props.onProceedRemoval(props.token);
        }
    }

    useEffect(() => {
        if ('function' === typeof props.onCheckRow) {
            props.onCheckRow(props.token, selected);
        }
    }, [selected]);

    useEffect(() => {
        setSelected(props.selectedRow);
    }, [props.selectedRow]);

    return (
        <div className="item manage-item manage-media-item">
            <div className="mi-checkbox">
                <input type="checkbox" checked={selected} onChange={onRowCheck} />
            </div>
            <div className="mi-title">
                <ManageItemTitle title={props.title} url={props.url} />
                {props.hideDeleteAction ? null : (
                    <ManageItemMediaActions
                        containerRef={actionsContainerRef}
                        title={props.title}
                        token={props.token}
                        onProceed={onClickProceed}
                        onMigratePaths={props.onMigratePaths}
                        onCheckMigratePaths={props.onCheckMigratePaths}
                    />
                )}
            </div>
            <div className="mi-added">
                <ManageItemDate date={props.add_date} />
            </div>
            <div className="mi-author">
                <ManageItemMediaAuthor name={props.author_name} url={props.author_url} />
            </div>
            <div className="mi-type">
                {void 0 === props.media_type ? <i className="non-available">N/A</i> : props.media_type}
            </div>
            <div className="mi-encoding">
                {void 0 === props.encoding_status ? <i className="non-available">N/A</i> : props.encoding_status}
            </div>
            <div className="mi-state">
                {void 0 === props.state ? <i className="non-available">N/A</i> : props.state}
            </div>
            <div className="mi-reviewed">
                {void 0 === props.is_reviewed ? (
                    <i className="non-available">N/A</i>
                ) : props.is_reviewed ? (
                    <MaterialIcon type="check_circle" />
                ) : (
                    <MaterialIcon type="cancel" />
                )}
            </div>
            <div className="mi-featured">
                {void 0 === props.featured ? (
                    <i className="non-available">N/A</i>
                ) : props.featured ? (
                    <MaterialIcon type="check_circle" />
                ) : (
                    '-'
                )}
            </div>
            <div className="mi-reported">
                {void 0 === props.reported_times ? (
                    <i className="non-available">N/A</i>
                ) : 0 === props.reported_times ? (
                    <span>-</span>
                ) : (
                    <span className="reported-number">
                        {props.reported_times} {'time' + (1 < props.reported_times ? 's' : '')}
                    </span>
                )}
            </div>
        </div>
    );
}
